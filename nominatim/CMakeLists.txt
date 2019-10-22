add_executable(nominatim export.c geometry.cpp import.c index.c input.c nominatim.c postgresql.c sprompt.c)
include(CheckSymbolExists)

CHECK_SYMBOL_EXISTS(bswap_32 "byteswap.h" HAVE_BYTESWAP)
CHECK_SYMBOL_EXISTS(bswap32 "sys/endian.h" HAVE_SYS_ENDIAN)

target_compile_definitions(nominatim
    PRIVATE HAVE_BYTESWAP=$<BOOL:${HAVE_BYTESWAP}>
    PRIVATE HAVE_SYS_ENDIAN=$<BOOL:${HAVE_SYS_ENDIAN}>
)

target_link_libraries(nominatim ${LIBXML2_LIBRARIES} ${ZLIB_LIBRARIES} ${BZIP2_LIBRARIES} ${PostgreSQL_LIBRARIES} ${CMAKE_THREAD_LIBS_INIT})

