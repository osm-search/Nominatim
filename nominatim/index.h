#ifndef INDEX_H
#define INDEX_H

#include <libxml/encoding.h>
#include <libxml/xmlwriter.h>

struct index_thread_data
{
    pthread_t thread;
    PGconn * conn;
    PGresult * res;
    int tuples;
    int * count;
    pthread_mutex_t * count_mutex;
    xmlTextWriterPtr writer;
    pthread_mutex_t * writer_mutex;
    unsigned table;
};
void nominatim_index(int rank_min, int rank_max, int num_threads, const char *conninfo, const char *structuredoutputfile);
void *nominatim_indexThread(void * thread_data_in);

#endif
