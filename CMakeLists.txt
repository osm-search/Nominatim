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

set(BUILD_TESTS on)
set(WITH_LUA off)
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

set(CUSTOMFILES
    settings/settings.php
    settings/phrase_settings.php
    website/deletable.php
    website/details.php
    website/hierarchy.php
    website/lookup.php
    website/polygons.php
    website/reverse.php
    website/search.php
    website/status.php
    utils/blocks.php
    utils/country_languages.php
    utils/imports.php
    utils/importWikipedia.php
    utils/query.php
    utils/server_compare.php
    utils/setup.php
    utils/specialphrases.php
    utils/update.php
    utils/warm.php
   )

foreach (cfile ${CUSTOMFILES})
    configure_file(${PROJECT_SOURCE_DIR}/${cfile} ${PROJECT_BINARY_DIR}/${cfile})
endforeach()

set(WEBPATHS css images js)

foreach (wp ${WEBPATHS})
    execute_process(
        COMMAND ln -sf ${PROJECT_SOURCE_DIR}/website/${wp} ${PROJECT_BINARY_DIR}/website/
    )
endforeach()


#-----------------------------------------------------------------------------
#
# Tests
#
#-----------------------------------------------------------------------------

include(CTest)

set(TEST_BDD db osm2pgsql api)

foreach (test ${TEST_BDD})
    add_test(NAME bdd_${test}
             COMMAND lettuce features/${test}
             WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}/tests)
    set_tests_properties(bdd_${test}
        PROPERTIES ENVIRONMENT "NOMINATIM_DIR=${PROJECT_BINARY_DIR}")
endforeach()

add_test(NAME php
         COMMAND phpunit ./
         WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}/tests-php)

#-----------------------------------------------------------------------------

add_subdirectory(module)
add_subdirectory(nominatim)

#-----------------------------------------------------------------------------
