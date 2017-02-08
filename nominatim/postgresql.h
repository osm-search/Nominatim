/*
*/

#ifndef POSTGRESQL_H
#define POSTGRESQL_H

#define PG_OID_INT8			20
#define PG_OID_INT4			23

// #include <byteswap.h>
#ifdef __i386__ /* Are we on an x86? */
#define GCC_VERSION (__GNUC__ * 10000 + __GNUC_MINOR__ * 100 + __GNUC_PATCHLEVEL__)
#if GCC_VERSION >= 40300 /* Modern enough to have byteswap intrinsics? */
#define ENDIAN_SWAP_INT __builtin_bswap32
#elif GCC_VERSION >= 20000 /* 'Modern' enough to offer byteswap.h */
#include <byteswap.h>
#define ENDIAN_SWAP_INT bswap_32
#endif /* GCC >= 4.3 */
#endif /* x86 or later */

#if __BYTE_ORDER == __BIG_ENDIAN
#define PGint16(x)	(x)
#define PGint32(x)	(x)
#define PGint64(x)	(x)
#else
#define PGint16(x)	__bswap_16 (x)
#define PGint32(x)	__bswap_32 (x)
#define PGint64(x)	__bswap_64 (x)
#endif

const char *build_conninfo(const char *db, const char *username, const char *password, const char *host, const char *port);

#endif
