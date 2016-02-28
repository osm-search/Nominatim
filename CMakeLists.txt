#-----------------------------------------------------------------------------
#
#  CMake Config
#
#  Nominatim
#
#-----------------------------------------------------------------------------

cmake_minimum_required(VERSION 2.8 FATAL_ERROR)
list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")


#-----------------------------------------------------------------------------
#
#  Project version
#
#-----------------------------------------------------------------------------

project(nominatim)

set(NOMINATIM_VERSION_MAJOR 2)
set(NOMINATIM_VERSION_MINOR 5)

set(NOMINATIM_VERSION "${NOMINATIM_VERSION_MAJOR}.${NOMINATIM_VERSION_MINOR}")

add_definitions(-DNOMINATIM_VERSION="${NOMINATIM_VERSION}")


#-----------------------------------------------------------------------------
#
#  Find external dependencies
#
#-----------------------------------------------------------------------------

add_subdirectory(osm2pgsql)

find_package(Threads REQUIRED)

unset(PostgreSQL_TYPE_INCLUDE_DIR CACHE)
set(PostgreSQL_TYPE_INCLUDE_DIR "/usr/include/")
find_package(PostgreSQL REQUIRED)
include_directories(${PostgreSQL_INCLUDE_DIRS})

find_program(PG_CONFIG pg_config)
execute_process(COMMAND ${PG_CONFIG} --pgxs
                OUTPUT_VARIABLE PGXS
                OUTPUT_STRIP_TRAILING_WHITESPACE)

find_package(ZLIB REQUIRED)

find_package(BZip2 REQUIRED)

find_package(LibXml2 REQUIRED)
include_directories(${LIBXML2_INCLUDE_DIR})

#-----------------------------------------------------------------------------
#
# Setup settings and paths
#
#-----------------------------------------------------------------------------

configure_file(
    ${PROJECT_SOURCE_DIR}/settings/settings.php
    ${PROJECT_BINARY_DIR}/settings/settings.php
)

configure_file(
    ${PROJECT_SOURCE_DIR}/settings/phrase_settings.php
    ${PROJECT_BINARY_DIR}/settings/phrase_settings.php
)

execute_process(
    COMMAND ln -s -t ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}/utils
)

#-----------------------------------------------------------------------------

add_subdirectory(module)
add_subdirectory(nominatim)

#-----------------------------------------------------------------------------
