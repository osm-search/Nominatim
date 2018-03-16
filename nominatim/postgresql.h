/*
*/

#ifndef POSTGRESQL_H
#define POSTGRESQL_H

#define PG_OID_INT8			20
#define PG_OID_INT4			23

#if HAVE_BYTESWAP
#include <byteswap.h>
#define PG_BSWAP32(x) bswap_32(x)
#define PG_BSWAP64(x) bswap_64(x)
#elif HAVE_SYS_ENDIAN
#include <sys/endian.h>
#define PG_BSWAP32(x) bswap32(x)
#define PG_BSWAP64(x) bswap64(x)
#else
#error "No appropriate byteswap found for your system."
#endif

#if defined(__BYTE_ORDER__) && (__BYTE_ORDER__ == __ORDER_BIG_ENDIAN__)
#define PGint32(x)	(x)
#define PGint64(x)	(x)
#elif defined(__BYTE_ORDER__) &&  (__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__)
#define PGint32(x)	PG_BSWAP32(x)
#define PGint64(x)	PG_BSWAP64(x)
#elif defined(_BYTE_ORDER) && (_BYTE_ORDER == _BIG_ENDIAN)
#define PGint32(x)	(x)
#define PGint64(x)	(x)
#elif defined(_BYTE_ORDER) &&  (_BYTE_ORDER == _LITTLE_ENDIAN)
#define PGint32(x)	PG_BSWAP32(x)
#define PGint64(x)	PG_BSWAP64(x)
#else
#error "Cannot determine byte order."
#endif

const char *build_conninfo(const char *db, const char *username, const char *password, const char *host, const char *port);

#endif
