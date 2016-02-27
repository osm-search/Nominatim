add_executable(nominatim export.c geometry.cpp import.c index.c input.c nominatim.c postgresql.c sprompt.c)

target_link_libraries(nominatim ${LIBXML2_LIBRARIES} ${ZLIB_LIBRARIES} ${BZIP2_LIBRARIES} ${PostgreSQL_LIBRARIES} ${CMAKE_THREAD_LIBS_INIT})

