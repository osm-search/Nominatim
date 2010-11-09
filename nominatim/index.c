/*
*/

#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <pthread.h>
#include <time.h>
#include <stdint.h>

#include <libpq-fe.h>

#include "nominatim.h"
#include "index.h"
#include "export.h"
#include "postgresql.h"

extern int verbose;

void nominatim_index(int rank_min, int rank_max, int num_threads, const char *conninfo, const char *structuredoutputfile)
{
	struct index_thread_data * thread_data;
	pthread_mutex_t count_mutex = PTHREAD_MUTEX_INITIALIZER;
	int tuples, count, sleepcount;

	time_t rankStartTime;
	int rankTotalTuples;
	int rankCountTuples;
	float rankPerSecond;

	PGconn *conn;
	PGresult * res;
	PGresult * resSectors;
	PGresult * resPlaces;

	int rank;
	int i;
	int iSector;

    const char *paramValues[2];
    int         paramLengths[2];
    int         paramFormats[2];
    uint32_t    paramRank;
    uint32_t    paramSector;
    uint32_t    sector;

    xmlTextWriterPtr writer;
	pthread_mutex_t writer_mutex = PTHREAD_MUTEX_INITIALIZER;

    Oid pg_prepare_params[2];

    conn = PQconnectdb(conninfo);
    if (PQstatus(conn) != CONNECTION_OK) {
        fprintf(stderr, "Connection to database failed: %s\n", PQerrorMessage(conn));
        exit(EXIT_FAILURE);
    }

    pg_prepare_params[0] = PG_OID_INT4;
    res = PQprepare(conn, "index_sectors",
    	"select geometry_sector,count(*) from placex where rank_search = $1 and indexed_status > 0 group by geometry_sector order by geometry_sector",
    	1, pg_prepare_params);
    if (PQresultStatus(res) != PGRES_COMMAND_OK)
    {
        fprintf(stderr, "Failed preparing index_sectors: %s\n", PQerrorMessage(conn));
        exit(EXIT_FAILURE);
    }
    PQclear(res);

    pg_prepare_params[0] = PG_OID_INT4;
    res = PQprepare(conn, "index_nosectors",
    	"select 0::integer,count(*) from placex where rank_search = $1 and indexed_status > 0",
    	1, pg_prepare_params);
    if (PQresultStatus(res) != PGRES_COMMAND_OK)
    {
        fprintf(stderr, "Failed preparing index_sectors: %s\n", PQerrorMessage(conn));
        exit(EXIT_FAILURE);
    }
    PQclear(res);

    pg_prepare_params[0] = PG_OID_INT4;
    pg_prepare_params[1] = PG_OID_INT4;
    res = PQprepare(conn, "index_sector_places",
    	"select place_id from placex where rank_search = $1 and geometry_sector = $2 and indexed_status > 0",
    	2, pg_prepare_params);
    if (PQresultStatus(res) != PGRES_COMMAND_OK)
    {
        fprintf(stderr, "Failed preparing index_sector_places: %s\n", PQerrorMessage(conn));
        exit(EXIT_FAILURE);
    }
    PQclear(res);

    pg_prepare_params[0] = PG_OID_INT4;
    res = PQprepare(conn, "index_nosector_places",
    	"select place_id from placex where rank_search = $1 and indexed_status > 0 order by geometry_sector",
    	1, pg_prepare_params);
    if (PQresultStatus(res) != PGRES_COMMAND_OK)
    {
        fprintf(stderr, "Failed preparing index_nosector_places: %s\n", PQerrorMessage(conn));
        exit(EXIT_FAILURE);
    }
    PQclear(res);

    // Build the data for each thread
    thread_data = (struct index_thread_data *)malloc(sizeof(struct index_thread_data)*num_threads);
	for (i = 0; i < num_threads; i++)
	{
		thread_data[i].conn = PQconnectdb(conninfo);
	    if (PQstatus(thread_data[i].conn) != CONNECTION_OK) {
	        fprintf(stderr, "Connection to database failed: %s\n", PQerrorMessage(thread_data[i].conn));
	        exit(EXIT_FAILURE);
	    }

	    pg_prepare_params[0] = PG_OID_INT4;
	    res = PQprepare(thread_data[i].conn, "index_placex",
	    	"update placex set indexed_status = 0 where place_id = $1",
	    	1, pg_prepare_params);
	    if (PQresultStatus(res) != PGRES_COMMAND_OK)
	    {
	        fprintf(stderr, "Failed preparing index_placex: %s\n", PQerrorMessage(conn));
	        exit(EXIT_FAILURE);
	    }
	    PQclear(res);

	    nominatim_exportCreatePreparedQueries(thread_data[i].conn);
	}

	// Create the output file
	writer = NULL;
	if (structuredoutputfile)
	{
		writer = nominatim_exportXMLStart(structuredoutputfile);
	}

    fprintf(stderr, "Starting indexing rank (%i to %i) using %i treads\n", rank_min, rank_max, num_threads);

    for (rank = rank_min; rank <= rank_max; rank++)
    {
    	printf("Starting rank %d\n", rank);
    	rankCountTuples = 0;
    	rankPerSecond = 0;

        paramRank = PGint32(rank);
        paramValues[0] = (char *)&paramRank;
        paramLengths[0] = sizeof(paramRank);
        paramFormats[0] = 1;
		if (rank < 16)
	        resSectors = PQexecPrepared(conn, "index_nosectors", 1, paramValues, paramLengths, paramFormats, 1);
		else
	        resSectors = PQexecPrepared(conn, "index_sectors", 1, paramValues, paramLengths, paramFormats, 1);
        if (PQresultStatus(resSectors) != PGRES_TUPLES_OK)
        {
            fprintf(stderr, "index_sectors: SELECT failed: %s", PQerrorMessage(conn));
            PQclear(resSectors);
            exit(EXIT_FAILURE);
        }
		if (PQftype(resSectors, 0) != PG_OID_INT4)
		{
            fprintf(stderr, "Sector value has unexpected type\n");
            PQclear(resSectors);
            exit(EXIT_FAILURE);
		}
		if (PQftype(resSectors, 1) != PG_OID_INT8)
		{
            fprintf(stderr, "Sector value has unexpected type\n");
            PQclear(resSectors);
            exit(EXIT_FAILURE);
		}

		rankTotalTuples = 0;
    	for (iSector = 0; iSector < PQntuples(resSectors); iSector++)
    	{
    		rankTotalTuples += PGint64(*((uint64_t *)PQgetvalue(resSectors, iSector, 1)));
    	}

    	rankStartTime = time(0);
    	for (iSector = 0; iSector < PQntuples(resSectors); iSector++)
    	{
			sector = PGint32(*((uint32_t *)PQgetvalue(resSectors, iSector, 0)));
	    	//printf("\n Starting sector %d size %ld\n", sector, PGint64(*((uint64_t *)PQgetvalue(resSectors, iSector, 1))));

			// Get all the place_id's for this sector
		    paramRank = PGint32(rank);
	    	paramValues[0] = (char *)&paramRank;
		    paramLengths[0] = sizeof(paramRank);
		    paramFormats[0] = 1;
	    	paramSector = PGint32(sector);
	        paramValues[1] = (char *)&paramSector;
			paramLengths[1] = sizeof(paramSector);
		    paramFormats[1] = 1;
			if (rank < 16)
		        resPlaces = PQexecPrepared(conn, "index_nosector_places", 1, paramValues, paramLengths, paramFormats, 1);
			else
		        resPlaces = PQexecPrepared(conn, "index_sector_places", 2, paramValues, paramLengths, paramFormats, 1);
	        if (PQresultStatus(resPlaces) != PGRES_TUPLES_OK)
	        {
	            fprintf(stderr, "index_sector_places: SELECT failed: %s", PQerrorMessage(conn));
	            PQclear(resPlaces);
	            exit(EXIT_FAILURE);
	        }
			if (PQftype(resPlaces, 0) != PG_OID_INT4)
			{
	            fprintf(stderr, "Place_id value has unexpected type\n");
	            PQclear(resPlaces);
	            exit(EXIT_FAILURE);
			}

			count = 0;
			rankPerSecond = 0;
			tuples = PQntuples(resPlaces);

			if (tuples > 0)
	        {
				// Spawn threads
				for (i = 0; i < num_threads; i++)
				{
					thread_data[i].res = resPlaces;
					thread_data[i].tuples = tuples;
					thread_data[i].count = &count;
					thread_data[i].count_mutex = &count_mutex;
					thread_data[i].writer = writer;
					thread_data[i].writer_mutex = &writer_mutex;
					pthread_create(&thread_data[i].thread, NULL, &nominatim_indexThread, (void *)&thread_data[i]);
				}

				// Monitor threads to give user feedback
				sleepcount = 0;
				while(count < tuples)
				{
					usleep(1000);

					// Aim for one update per second
					if (sleepcount++ > 500)
					{
						rankPerSecond = ((float)rankCountTuples + (float)count) / MAX(difftime(time(0), rankStartTime),1);
						printf("  Done %i in %i @ %f per second - Rank %i ETA (seconds): %f\n", (rankCountTuples + count), (int)(difftime(time(0), rankStartTime)), rankPerSecond, rank, ((float)(rankTotalTuples - (rankCountTuples + count)))/rankPerSecond);
						sleepcount = 0;
					}
				}

				// Wait for everything to finish
				for (i = 0; i < num_threads; i++)
				{
					pthread_join(thread_data[i].thread, NULL);
				}

				rankCountTuples += tuples;
	        }

			// Finished sector
			rankPerSecond = (float)rankCountTuples / MAX(difftime(time(0), rankStartTime),1);
			printf("  Done %i in %i @ %f per second - ETA (seconds): %f\n", rankCountTuples, (int)(difftime(time(0), rankStartTime)), rankPerSecond, ((float)(rankTotalTuples - rankCountTuples))/rankPerSecond);

            PQclear(resPlaces);

    	}
        // Finished rank
		printf("\r  Done %i in %i @ %f per second - FINISHED                      \n\n", rankCountTuples, (int)(difftime(time(0), rankStartTime)), rankPerSecond);

        PQclear(resSectors);
    }

    if (writer)
    {
    	nominatim_exportXMLEnd(writer);
    }
}

void *nominatim_indexThread(void * thread_data_in)
{
	struct index_thread_data * thread_data = (struct index_thread_data * )thread_data_in;

	PGresult   *res;

    const char *paramValues[1];
    int         paramLengths[1];
    int         paramFormats[1];
    uint32_t    paramPlaceID;
    uint32_t 	place_id;
	time_t 		updateStartTime;

	while(1)
	{
		pthread_mutex_lock( thread_data->count_mutex );
		if (*(thread_data->count) >= thread_data->tuples)
		{
			pthread_mutex_unlock( thread_data->count_mutex );
			break;
		}

		place_id = PGint32(*((uint32_t *)PQgetvalue(thread_data->res, *thread_data->count, 0)));
		(*thread_data->count)++;

		pthread_mutex_unlock( thread_data->count_mutex );

		if (verbose) printf("  Processing place_id %d\n", place_id);
		
		updateStartTime = time(0);
		paramPlaceID = PGint32(place_id);
        paramValues[0] = (char *)&paramPlaceID;
        paramLengths[0] = sizeof(paramPlaceID);
        paramFormats[0] = 1;
        res = PQexecPrepared(thread_data->conn, "index_placex", 1, paramValues, paramLengths, paramFormats, 1);
        if (PQresultStatus(res) != PGRES_COMMAND_OK)
        {
            fprintf(stderr, "index_placex: UPDATE failed: %s", PQerrorMessage(thread_data->conn));
            PQclear(res);
            exit(EXIT_FAILURE);
        }
        PQclear(res);
		if (difftime(time(0), updateStartTime) > 1) printf("  Slow place_id %d\n", place_id);

        if (thread_data->writer)
        {
        	nominatim_exportPlace(place_id, thread_data->conn, thread_data->writer, thread_data->writer_mutex);
        }
	}

	return NULL;
}
