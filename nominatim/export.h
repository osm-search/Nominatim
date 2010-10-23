#ifndef EXPORT_H
#define EXPORT_H

#include <libxml/encoding.h>
#include <libxml/xmlwriter.h>
#include <stdint.h>

void nominatim_export(int rank_min, int rank_max, const char *conninfo, const char *structuredoutputfile);
void nominatim_exportCreatePreparedQueries(PGconn * conn);
xmlTextWriterPtr nominatim_exportXMLStart(const char *structuredoutputfile);
void nominatim_exportXMLEnd(xmlTextWriterPtr writer);
void nominatim_exportPlace(uint64_t place_id, PGconn * conn, xmlTextWriterPtr writer, pthread_mutex_t * writer_mutex);
const char * getRankLabel(int rank);

#endif
