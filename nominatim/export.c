/*
*/

#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <time.h>
#include <stdint.h>
#include <pthread.h>

#include <libpq-fe.h>

#include "nominatim.h"
#include "export.h"
#include "postgresql.h"

extern int verbose;

void nominatim_export(int rank_min, int rank_max, const char *conninfo, const char *structuredoutputfile)
{
    xmlTextWriterPtr writer;

	int rankTotalDone;

	PGconn *conn;
	PGresult * res;
	PGresult * resSectors;
	PGresult * resPlaces;

	int rank;
	int i;
	int iSector;
    int tuples;

    const char *paramValues[2];
    int         paramLengths[2];
    int         paramFormats[2];
    uint32_t    paramRank;
    uint32_t    paramSector;
    uint32_t    sector;

    Oid pg_prepare_params[2];

	conn = PQconnectdb(conninfo);
    if (PQstatus(conn) != CONNECTION_OK) {
        fprintf(stderr, "Connection to database failed: %s\n", PQerrorMessage(conn));
        exit(EXIT_FAILURE);
    }

    pg_prepare_params[0] = PG_OID_INT4;
    res = PQprepare(conn, "index_sectors",
    	"select geometry_sector,count(*) from placex where rank_search = $1 and indexed = true group by geometry_sector order by geometry_sector",
    	1, pg_prepare_params);
    if (PQresultStatus(res) != PGRES_COMMAND_OK) exit(EXIT_FAILURE);
    PQclear(res);

    pg_prepare_params[0] = PG_OID_INT4;
    pg_prepare_params[1] = PG_OID_INT4;
    res = PQprepare(conn, "index_sector_places",
    	"select place_id from placex where rank_search = $1 and geometry_sector = $2",
    	2, pg_prepare_params);
    if (PQresultStatus(res) != PGRES_COMMAND_OK) exit(EXIT_FAILURE);
    PQclear(res);

    nominatim_exportCreatePreparedQueries(conn);

	// Create the output file
	writer = nominatim_exportXMLStart(structuredoutputfile);

    for (rank = rank_min; rank <= rank_max; rank++)
    {
    	printf("Starting rank %d\n", rank);

        paramRank = PGint32(rank);
        paramValues[0] = (char *)&paramRank;
        paramLengths[0] = sizeof(paramRank);
        paramFormats[0] = 1;
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

		rankTotalDone = 0;
    	for (iSector = 0; iSector < PQntuples(resSectors); iSector++)
    	{
			sector = PGint32(*((uint32_t *)PQgetvalue(resSectors, iSector, 0)));

			// Get all the place_id's for this sector
	        paramRank = PGint32(rank);
	        paramValues[0] = (char *)&paramRank;
	        paramLengths[0] = sizeof(paramRank);
	        paramFormats[0] = 1;
	        paramSector = PGint32(sector);
	        paramValues[1] = (char *)&paramSector;
	        paramLengths[1] = sizeof(paramSector);
	        paramFormats[1] = 1;
	        resPlaces = PQexecPrepared(conn, "index_sector_places", 2, paramValues, paramLengths, paramFormats, 1);
	        if (PQresultStatus(resPlaces) != PGRES_TUPLES_OK)
	        {
	            fprintf(stderr, "index_sector_places: SELECT failed: %s", PQerrorMessage(conn));
	            PQclear(resPlaces);
	            exit(EXIT_FAILURE);
	        }
			if (PQftype(resPlaces, 0) != PG_OID_INT8)
			{
	            fprintf(stderr, "Place_id value has unexpected type\n");
	            PQclear(resPlaces);
	            exit(EXIT_FAILURE);
			}

			tuples = PQntuples(resPlaces);
			for(i = 0; i < tuples; i++)
			{
				nominatim_exportPlace(PGint64(*((uint64_t *)PQgetvalue(resPlaces, i, 0))), conn, writer, NULL);
				rankTotalDone++;
				if (rankTotalDone%1000 == 0) printf("Done %i (k)\n", rankTotalDone/1000);
	        }
            PQclear(resPlaces);
    	}
        PQclear(resSectors);
    }

    nominatim_exportXMLEnd(writer);

    PQfinish(conn);
}

void nominatim_exportCreatePreparedQueries(PGconn * conn)
{
    Oid pg_prepare_params[2];
	PGresult * res;

    pg_prepare_params[0] = PG_OID_INT8;
    res = PQprepare(conn, "placex_details",
    	"select osm_type, osm_id, class, type, name, housenumber, country_code, ST_AsText(geometry), admin_level, rank_address, rank_search from placex where place_id = $1",
    	1, pg_prepare_params);
    if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		fprintf(stderr, "Error preparing placex_details: %s", PQerrorMessage(conn));
		exit(EXIT_FAILURE);
	}
    PQclear(res);

    pg_prepare_params[0] = PG_OID_INT8;
    res = PQprepare(conn, "placex_address",
    	"select osm_type,osm_id,class,type,distance,cached_rank_address from place_addressline join placex on (address_place_id = placex.place_id) where isaddress and place_addressline.place_id = $1 and address_place_id != place_addressline.place_id order by cached_rank_address asc",
    	1, pg_prepare_params);
    if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		fprintf(stderr, "Error preparing placex_address: %s", PQerrorMessage(conn));
		exit(EXIT_FAILURE);
	}
    PQclear(res);

    pg_prepare_params[0] = PG_OID_INT8;
    res = PQprepare(conn, "placex_names",
    	"select (each(name)).key,(each(name)).value from (select name as name from placex where place_id = $1) as x",
    	1, pg_prepare_params);
    if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		fprintf(stderr, "Error preparing placex_names: %s", PQerrorMessage(conn));
		exit(EXIT_FAILURE);
	}
    PQclear(res);
}

xmlTextWriterPtr nominatim_exportXMLStart(const char *structuredoutputfile)
{
    xmlTextWriterPtr writer;

    writer = xmlNewTextWriterFilename(structuredoutputfile, 0);
	if (writer==NULL)
	{
		fprintf(stderr, "Unable to open %s\n", structuredoutputfile);
		exit(EXIT_FAILURE);
	}
	xmlTextWriterSetIndent(writer, 1);
    if (xmlTextWriterStartDocument(writer, NULL, "UTF8", NULL) < 0)
    {
		fprintf(stderr, "xmlTextWriterStartDocument failed\n");
		exit(EXIT_FAILURE);
    }
    if (xmlTextWriterStartElement(writer, BAD_CAST "osmStructured") < 0)
    {
		fprintf(stderr, "xmlTextWriterStartElement failed\n");
		exit(EXIT_FAILURE);
    }
    if (xmlTextWriterWriteAttribute(writer, BAD_CAST "version", BAD_CAST "0.1") < 0)
    {
		fprintf(stderr, "xmlTextWriterWriteAttribute failed\n");
		exit(EXIT_FAILURE);
    }
    if (xmlTextWriterWriteAttribute(writer, BAD_CAST "generator", BAD_CAST "Nominatim") < 0)
    {
		fprintf(stderr, "xmlTextWriterWriteAttribute failed\n");
		exit(EXIT_FAILURE);
    }
    if (xmlTextWriterStartElement(writer, BAD_CAST "add") < 0)
    {
		fprintf(stderr, "xmlTextWriterStartElement failed\n");
		exit(EXIT_FAILURE);
    }

    return writer;
}

void nominatim_exportXMLEnd(xmlTextWriterPtr writer)
{
	// End <add>
    if (xmlTextWriterEndElement(writer) < 0)
    {
		fprintf(stderr, "xmlTextWriterEndElement failed\n");
		exit(EXIT_FAILURE);
    }
	// End <osmStructured>
    if (xmlTextWriterEndElement(writer) < 0)
    {
		fprintf(stderr, "xmlTextWriterEndElement failed\n");
		exit(EXIT_FAILURE);
    }
    if (xmlTextWriterEndDocument(writer) < 0)
    {
		fprintf(stderr, "xmlTextWriterEndDocument failed\n");
		exit(EXIT_FAILURE);
    }
    xmlFreeTextWriter(writer);
}

/*
 * Requirements: the prepared queries must exist
 */
void nominatim_exportPlace(uint64_t place_id, PGconn * conn, xmlTextWriterPtr writer, pthread_mutex_t * writer_mutex)
{
	PGresult * 		res;
	PGresult * 		resNames;
	PGresult * 		resAddress;

	int 			i;

    const char *	paramValues[1];
    int         	paramLengths[1];
    int         	paramFormats[1];
    uint64_t    	paramPlaceID;


	paramPlaceID = PGint64(place_id);
    paramValues[0] = (char *)&paramPlaceID;
    paramLengths[0] = sizeof(paramPlaceID);
    paramFormats[0] = 1;

    res = PQexecPrepared(conn, "placex_details", 1, paramValues, paramLengths, paramFormats, 0);
	if (PQresultStatus(res) != PGRES_TUPLES_OK)
	{
		fprintf(stderr, "placex_details: SELECT failed: %s", PQerrorMessage(conn));
		PQclear(res);
		exit(EXIT_FAILURE);
	}

	resNames = PQexecPrepared(conn, "placex_names", 1, paramValues, paramLengths, paramFormats, 0);
	if (PQresultStatus(resNames) != PGRES_TUPLES_OK)
	{
		fprintf(stderr, "placex_names: SELECT failed: %s", PQerrorMessage(conn));
		PQclear(resNames);
		exit(EXIT_FAILURE);
	}

	resAddress = PQexecPrepared(conn, "placex_address", 1, paramValues, paramLengths, paramFormats, 0);
	if (PQresultStatus(resAddress) != PGRES_TUPLES_OK)
	{
		fprintf(stderr, "placex_address: SELECT failed: %s", PQerrorMessage(conn));
		PQclear(resAddress);
		exit(EXIT_FAILURE);
	}

	if (writer_mutex) pthread_mutex_lock( writer_mutex );

	xmlTextWriterStartElement(writer, BAD_CAST "feature");
	xmlTextWriterWriteFormatAttribute(writer, BAD_CAST "place_id", "%li", place_id);
	xmlTextWriterWriteAttribute(writer, BAD_CAST "type", BAD_CAST PQgetvalue(res, 0, 0));
	xmlTextWriterWriteAttribute(writer, BAD_CAST "id", BAD_CAST PQgetvalue(res, 0, 1));
	xmlTextWriterWriteAttribute(writer, BAD_CAST "key", BAD_CAST PQgetvalue(res, 0, 2));
	xmlTextWriterWriteAttribute(writer, BAD_CAST "value", BAD_CAST PQgetvalue(res, 0, 3));
	xmlTextWriterWriteAttribute(writer, BAD_CAST "rank", BAD_CAST PQgetvalue(res, 0, 9));
	xmlTextWriterWriteAttribute(writer, BAD_CAST "importance", BAD_CAST PQgetvalue(res, 0, 10));

	if (PQgetvalue(res, 0, 4) && strlen(PQgetvalue(res, 0, 4)))
	{
		xmlTextWriterStartElement(writer, BAD_CAST "names");

		for(i = 0; i < PQntuples(resNames); i++)
		{
			xmlTextWriterStartElement(writer, BAD_CAST "name");
			xmlTextWriterWriteAttribute(writer, BAD_CAST "type", BAD_CAST PQgetvalue(resNames, i, 0));
			xmlTextWriterWriteString(writer, BAD_CAST PQgetvalue(resNames, i, 1));
			xmlTextWriterEndElement(writer);
		}

		xmlTextWriterEndElement(writer);
	}

	if (PQgetvalue(res, 0, 5) && strlen(PQgetvalue(res, 0, 5)))
	{
		xmlTextWriterStartElement(writer, BAD_CAST "houseNumber");
		xmlTextWriterWriteString(writer, BAD_CAST PQgetvalue(res, 0, 5));
		xmlTextWriterEndElement(writer);
	}

	if (PQgetvalue(res, 0, 8) && strlen(PQgetvalue(res, 0, 8)))
	{
		xmlTextWriterStartElement(writer, BAD_CAST "adminLevel");
		xmlTextWriterWriteString(writer, BAD_CAST PQgetvalue(res, 0, 8));
		xmlTextWriterEndElement(writer);
	}

	if (PQgetvalue(res, 0, 6) && strlen(PQgetvalue(res, 0, 6)))
	{
		xmlTextWriterStartElement(writer, BAD_CAST "countryCode");
		xmlTextWriterWriteString(writer, BAD_CAST PQgetvalue(res, 0, 6));
		xmlTextWriterEndElement(writer);
	}

	if (PQntuples(resAddress) > 0)
	{
		xmlTextWriterStartElement(writer, BAD_CAST "address");
		for(i = 0; i < PQntuples(resAddress); i++)
		{
			xmlTextWriterStartElement(writer, BAD_CAST getRankLabel(atoi(PQgetvalue(resAddress, i, 5))));
			xmlTextWriterWriteAttribute(writer, BAD_CAST "rank", BAD_CAST PQgetvalue(resAddress, i, 5));
			xmlTextWriterWriteAttribute(writer, BAD_CAST "type", BAD_CAST PQgetvalue(resAddress, i, 0));
			xmlTextWriterWriteAttribute(writer, BAD_CAST "id", BAD_CAST PQgetvalue(resAddress, i, 1));
			xmlTextWriterWriteAttribute(writer, BAD_CAST "key", BAD_CAST PQgetvalue(resAddress, i, 2));
			xmlTextWriterWriteAttribute(writer, BAD_CAST "value", BAD_CAST PQgetvalue(resAddress, i, 3));
			xmlTextWriterWriteAttribute(writer, BAD_CAST "distance", BAD_CAST PQgetvalue(resAddress, i, 4));
			xmlTextWriterEndElement(writer);
		}
		xmlTextWriterEndElement(writer);
	}

	xmlTextWriterStartElement(writer, BAD_CAST "osmGeometry");
	xmlTextWriterWriteString(writer, BAD_CAST PQgetvalue(res, 0, 7));
	xmlTextWriterEndElement(writer);

	xmlTextWriterEndElement(writer); // </feature>

	if (writer_mutex) pthread_mutex_unlock( writer_mutex );

	PQclear(res);
	PQclear(resNames);
	PQclear(resAddress);
}

const char * getRankLabel(int rank)
{
	switch(rank)
	{
	case 0:
	case 1:
		return "continent";
	case 2:
	case 3:
		return "sea";
	case 4:
	case 5:
	case 6:
	case 7:
		return "country";
	case 8:
	case 9:
	case 10:
	case 11:
		return "state";
	case 12:
	case 13:
	case 14:
	case 15:
		return "county";
	case 16:
		return "city";
	case 17:
		return "town";
	case 18:
		return "village";
	case 19:
		return "unknown";
	case 20:
		return "suburb";
	case 21:
		return "postcode";
	case 22:
		return "neighborhood";
	case 23:
		return "postcode";
	case 24:
		return "unknown";
	case 25:
		return "postcode";
	case 26:
		return "street";
	case 27:
		return "access";
	case 28:
		return "building";
	case 29:
	default:
		return "other";
	}
}
