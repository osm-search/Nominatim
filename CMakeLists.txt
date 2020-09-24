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
set(NOMINATIM_VERSION_MINOR 5)
set(NOMINATIM_VERSION_PATCH 2)

set(NOMINATIM_VERSION "${NOMINATIM_VERSION_MAJOR}.${NOMINATIM_VERSION_MINOR}.${NOMINATIM_VERSION_PATCH}")

add_definitions(-DNOMINATIM_VERSION="${NOMINATIM_VERSION}")


#-----------------------------------------------------------------------------
#  Configuration
#-----------------------------------------------------------------------------

set(BUILD_IMPORTER on CACHE BOOL "Build everything for importing/updating the database")
set(BUILD_API on CACHE BOOL "Build everything for the API server")
set(BUILD_MODULE on CACHE BOOL "Build PostgreSQL module")
set(BUILD_TESTS on CACHE BOOL "Build test suite")
set(BUILD_DOCS on CACHE BOOL "Build documentation")
set(BUILD_OSM2PGSQL on CACHE BOOL "Build osm2pgsql (expert only)")

#-----------------------------------------------------------------------------
#  osm2pgsql (imports/updates only)
#-----------------------------------------------------------------------------

if (BUILD_IMPORTER AND BUILD_OSM2PGSQL)
    if (NOT EXISTS "${CMAKE_SOURCE_DIR}/osm2pgsql/CMakeLists.txt")
        message(FATAL_ERROR "The osm2pgsql directory is empty.\
        Did you forget to check out Nominatim recursively?\
        \nTry updating submodules with: git submodule update --init")
    endif()
    set(BUILD_TESTS_SAVED "${BUILD_TESTS}")
    set(BUILD_TESTS off)
    set(WITH_LUA off CACHE BOOL "")
    add_subdirectory(osm2pgsql)
    set(BUILD_TESTS ${BUILD_TESTS_SAVED})
endif()


#-----------------------------------------------------------------------------
#  python and pyosmium (imports/updates only)
#-----------------------------------------------------------------------------

if (BUILD_IMPORTER)
    find_package(PythonInterp 3)

    find_program(PYOSMIUM pyosmium-get-changes)
    if (NOT EXISTS "${PYOSMIUM}")
        set(PYOSMIUM_PATH "")
            message(WARNING "pyosmium-get-changes not found (required for updates)")
    else()
        set(PYOSMIUM_PATH "${PYOSMIUM}")
        message(STATUS "Using pyosmium-get-changes at ${PYOSMIUM_PATH}")
    endif()
endif()

#-----------------------------------------------------------------------------
# PHP
#-----------------------------------------------------------------------------

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
# import scripts and utilities (importer only)
#-----------------------------------------------------------------------------

if (BUILD_IMPORTER)
   set(CUSTOMSCRIPTS
       utils/check_import_finished.php
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
endif()

#-----------------------------------------------------------------------------
# webserver scripts (API only)
#-----------------------------------------------------------------------------

if (BUILD_API)
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

   foreach (script_source ${WEBSITESCRIPTS})
       configure_file(${PROJECT_SOURCE_DIR}/cmake/website.tmpl
                      ${PROJECT_BINARY_DIR}/${script_source})
   endforeach()

   set(WEBPATHS css images js)

   foreach (wp ${WEBPATHS})
       execute_process(
           COMMAND ln -sf ${PROJECT_SOURCE_DIR}/website/${wp} ${PROJECT_BINARY_DIR}/website/
       )
   endforeach()
endif()

#-----------------------------------------------------------------------------
# default settings
#-----------------------------------------------------------------------------

configure_file(${PROJECT_SOURCE_DIR}/settings/defaults.php
               ${PROJECT_BINARY_DIR}/settings/settings.php)

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

if (BUILD_TESTS)
    include(CTest)

    set(TEST_BDD db osm2pgsql api)

    foreach (test ${TEST_BDD})
        add_test(NAME bdd_${test}
                 COMMAND behave ${test}
                 WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}/test/bdd)
        set_tests_properties(bdd_${test}
            PROPERTIES ENVIRONMENT "NOMINATIM_DIR=${PROJECT_BINARY_DIR}")
    endforeach()

    add_test(NAME php
             COMMAND phpunit ./
             WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}/test/php)

    add_test(NAME phpcs
             COMMAND phpcs --report-width=120 --colors lib website utils
             WORKING_DIRECTORY ${PROJECT_SOURCE_DIR})
endif()

#-----------------------------------------------------------------------------
# Postgres module
#-----------------------------------------------------------------------------

if (BUILD_MODULE)
    add_subdirectory(module)
endif()

#-----------------------------------------------------------------------------
# Documentation
#-----------------------------------------------------------------------------

if (BUILD_DOCS)
   add_subdirectory(docs)
endif()
