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
set(NOMINATIM_VERSION_MINOR 6)
set(NOMINATIM_VERSION_PATCH 0)

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
    find_package(PythonInterp 3.5 REQUIRED)

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

if (BUILD_API OR BUILD_IMPORTER)
    if (NOT PHP_BIN)
         find_program (PHP_BIN php)
    endif()
    # sanity check if PHP binary exists
    if (NOT EXISTS ${PHP_BIN})
        message(FATAL_ERROR "PHP binary not found. Install php or provide location with -DPHP_BIN=/path/php ")
    endif()
    message (STATUS "Using PHP binary " ${PHP_BIN})
endif()

#-----------------------------------------------------------------------------
# import scripts and utilities (importer only)
#-----------------------------------------------------------------------------

if (BUILD_IMPORTER)
   set(CUSTOMSCRIPTS
       check_import_finished.php
       country_languages.php
       export.php
       query.php
       setup.php
       specialphrases.php
       update.php
       warm.php
      )

   foreach (script_source ${CUSTOMSCRIPTS})
       configure_file(${PROJECT_SOURCE_DIR}/cmake/script.tmpl
                      ${PROJECT_BINARY_DIR}/utils/${script_source})
   endforeach()

   configure_file(${PROJECT_SOURCE_DIR}/cmake/tool.tmpl
                  ${PROJECT_BINARY_DIR}/nominatim)
endif()

#-----------------------------------------------------------------------------
# Targets for running a development webserver from the build directory.
#-----------------------------------------------------------------------------

if (BUILD_API)
   add_custom_target(serve
           php -S 127.0.0.1:8088
           WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/website
   )

   add_custom_target(serve-global
           php -S 0.0.0.0:8088
           WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/website
   )
endif()

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

    add_test(NAME pylint
             COMMAND pylint3 nominatim
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
