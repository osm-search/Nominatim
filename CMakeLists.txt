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

set(NOMINATIM_VERSION_MAJOR 3)
set(NOMINATIM_VERSION_MINOR 2)
set(NOMINATIM_VERSION_PATCH 0)

set(NOMINATIM_VERSION "${NOMINATIM_VERSION_MAJOR}.${NOMINATIM_VERSION_MINOR}.${NOMINATIM_VERSION_PATCH}")

add_definitions(-DNOMINATIM_VERSION="${NOMINATIM_VERSION}")


#-----------------------------------------------------------------------------
#
#  Find external dependencies
#
#-----------------------------------------------------------------------------

set(BUILD_TESTS off CACHE BOOL "Build test suite" FORCE)
set(WITH_LUA off CACHE BOOL "Build with lua support" FORCE)

if (NOT EXISTS "${CMAKE_SOURCE_DIR}/osm2pgsql/CMakeLists.txt")
    message(FATAL_ERROR "The osm2pgsql directory is empty.\
    Did you forget to check out Nominatim recursively?\
    \nTry updating submodules with: git submodule update --init")
endif()
add_subdirectory(osm2pgsql)

find_package(Threads REQUIRED)

unset(PostgreSQL_TYPE_INCLUDE_DIR CACHE)
set(PostgreSQL_TYPE_INCLUDE_DIR "/usr/include/")
find_package(PostgreSQL REQUIRED)
include_directories(${PostgreSQL_INCLUDE_DIRS})
link_directories(${PostgreSQL_LIBRARY_DIRS})

find_program(PYOSMIUM pyosmium-get-changes)
if (NOT EXISTS "${PYOSMIUM}")
    set(PYOSMIUM_PATH "")
        message(WARNING "pyosmium-get-changes not found (required for updates)")
else()
    set(PYOSMIUM_PATH "${PYOSMIUM}")
    message(STATUS "Using pyosmium-get-changes at ${PYOSMIUM_PATH}")
endif()


find_program(PG_CONFIG pg_config)
execute_process(COMMAND ${PG_CONFIG} --pgxs
                OUTPUT_VARIABLE PGXS
                OUTPUT_STRIP_TRAILING_WHITESPACE)

if (NOT EXISTS "${PGXS}")
    message(FATAL_ERROR "Postgresql server package not found.")
endif()

find_package(ZLIB REQUIRED)

find_package(BZip2 REQUIRED)

find_package(LibXml2 REQUIRED)
include_directories(${LIBXML2_INCLUDE_DIR})

# Setting PHP binary variable as to command line (prevailing) or auto detect
if (NOT PHP_BIN)
     find_program (PHP_BIN php)
endif()
# sanity check if PHP binary exists
if (NOT EXISTS ${PHP_BIN})
    message(FATAL_ERROR "PHP binary not found. Install php or provide location with -DPHP_BIN=/path/php ")
endif()
message (STATUS "Using PHP binary " ${PHP_BIN})

#-----------------------------------------------------------------------------
#
# Setup settings and paths
#
#-----------------------------------------------------------------------------

set(WEBSITESCRIPTS
    website/deletable.php
    website/details.php
    website/hierarchy.php
    website/lookup.php
    website/polygons.php
    website/reverse.php
    website/search.php
    website/status.php
)

set(CUSTOMSCRIPTS
    utils/country_languages.php
    utils/importWikipedia.php
    utils/export.php
    utils/query.php
    utils/setup.php
    utils/specialphrases.php
    utils/update.php
    utils/warm.php
   )

foreach (script_source ${CUSTOMSCRIPTS})
    configure_file(${PROJECT_SOURCE_DIR}/cmake/script.tmpl
                   ${PROJECT_BINARY_DIR}/${script_source})
endforeach()

foreach (script_source ${WEBSITESCRIPTS})
    configure_file(${PROJECT_SOURCE_DIR}/cmake/website.tmpl
                   ${PROJECT_BINARY_DIR}/${script_source})
endforeach()

configure_file(${PROJECT_SOURCE_DIR}/settings/defaults.php
               ${PROJECT_BINARY_DIR}/settings/settings.php)

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
add_subdirectory(docs)

#-----------------------------------------------------------------------------
