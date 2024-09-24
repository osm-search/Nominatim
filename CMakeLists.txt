#-----------------------------------------------------------------------------
#
#  CMake Config
#
#  Nominatim
#
#-----------------------------------------------------------------------------

cmake_minimum_required(VERSION 3.0 FATAL_ERROR)
list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")


#-----------------------------------------------------------------------------
#
#  Project version
#
#-----------------------------------------------------------------------------

project(nominatim)

set(NOMINATIM_VERSION_MAJOR 4)
set(NOMINATIM_VERSION_MINOR 5)
set(NOMINATIM_VERSION_PATCH 0)

set(NOMINATIM_VERSION "${NOMINATIM_VERSION_MAJOR}.${NOMINATIM_VERSION_MINOR}.${NOMINATIM_VERSION_PATCH}")

add_definitions(-DNOMINATIM_VERSION="${NOMINATIM_VERSION}")

# Setting GIT_HASH
find_package(Git)
if (GIT_FOUND)
    execute_process(
        COMMAND "${GIT_EXECUTABLE}" log -1 --format=%h
        WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}
        OUTPUT_VARIABLE GIT_HASH
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
        )
endif()

#-----------------------------------------------------------------------------
#  Configuration
#-----------------------------------------------------------------------------

set(BUILD_IMPORTER on CACHE BOOL "Build everything for importing/updating the database")
set(BUILD_API on CACHE BOOL "Build everything for the API server")
set(BUILD_TESTS on CACHE BOOL "Build test suite")
set(BUILD_OSM2PGSQL on CACHE BOOL "Build osm2pgsql (expert only)")
set(INSTALL_MUNIN_PLUGINS on CACHE BOOL "Install Munin plugins for supervising Nominatim")

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
    add_subdirectory(osm2pgsql)
    set(BUILD_TESTS ${BUILD_TESTS_SAVED})
endif()


#-----------------------------------------------------------------------------
#  python (imports/updates only)
#-----------------------------------------------------------------------------

if (BUILD_IMPORTER OR BUILD_API)
    find_package(PythonInterp 3.7 REQUIRED)
endif()

#-----------------------------------------------------------------------------
# import scripts and utilities (importer only)
#-----------------------------------------------------------------------------

if (BUILD_IMPORTER)
   find_file(COUNTRY_GRID_FILE country_osm_grid.sql.gz
             PATHS ${PROJECT_SOURCE_DIR}/data
             NO_DEFAULT_PATH
             DOC "Location of the country grid file."
            )

   if (NOT COUNTRY_GRID_FILE)
       message(FATAL_ERROR "\nYou need to download the country_osm_grid first:\n"
                           "    wget -O ${PROJECT_SOURCE_DIR}/data/country_osm_grid.sql.gz https://www.nominatim.org/data/country_grid.sql.gz")
   endif()

   configure_file(${PROJECT_SOURCE_DIR}/cmake/tool.tmpl
                  ${PROJECT_BINARY_DIR}/nominatim)
endif()

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

if (BUILD_TESTS)
    include(CTest)

    set(TEST_BDD db osm2pgsql api)

    find_program(PYTHON_BEHAVE behave)
    find_program(PYLINT NAMES pylint3 pylint)
    find_program(PYTEST NAMES pytest py.test-3 py.test)

    if (PYTHON_BEHAVE)
        message(STATUS "Using Python behave binary ${PYTHON_BEHAVE}")
        foreach (test ${TEST_BDD})
            add_test(NAME bdd_${test}
                     COMMAND ${PYTHON_BEHAVE} ${test}
                     WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}/test/bdd)
            set_tests_properties(bdd_${test}
                PROPERTIES ENVIRONMENT "NOMINATIM_DIR=${PROJECT_BINARY_DIR}")
        endforeach()
    else()
        message(WARNING "behave not found. BDD tests disabled." )
    endif()

    if (PYLINT)
        message(STATUS "Using pylint binary ${PYLINT}")
        add_test(NAME pylint
                 COMMAND ${PYLINT} nominatim
                 WORKING_DIRECTORY ${PROJECT_SOURCE_DIR})
    else()
        message(WARNING "pylint not found. Python linting tests disabled.")
    endif()

    if (PYTEST)
        message(STATUS "Using pytest binary ${PYTEST}")
        add_test(NAME pytest
                 COMMAND ${PYTEST} test/python
                 WORKING_DIRECTORY ${PROJECT_SOURCE_DIR})
    else()
        message(WARNING "pytest not found. Python tests disabled." )
    endif()
endif()

#-----------------------------------------------------------------------------
# Installation
#-----------------------------------------------------------------------------


include(GNUInstallDirs)
set(NOMINATIM_DATADIR ${CMAKE_INSTALL_FULL_DATADIR}/${PROJECT_NAME})
set(NOMINATIM_LIBDIR ${CMAKE_INSTALL_FULL_LIBDIR}/${PROJECT_NAME})
set(NOMINATIM_CONFIGDIR ${CMAKE_INSTALL_FULL_SYSCONFDIR}/${PROJECT_NAME})
set(NOMINATIM_MUNINDIR ${CMAKE_INSTALL_FULL_DATADIR}/munin/plugins)

if (BUILD_IMPORTER)
    configure_file(${PROJECT_SOURCE_DIR}/cmake/tool-installed.tmpl installed.bin)
    install(PROGRAMS ${PROJECT_BINARY_DIR}/installed.bin
            DESTINATION ${CMAKE_INSTALL_BINDIR}
            RENAME nominatim)

    configure_file(${PROJECT_SOURCE_DIR}/cmake/paths-py-no-php.tmpl paths-py.installed)

    foreach (submodule nominatim_db nominatim_api)
        install(DIRECTORY src/${submodule}
                DESTINATION ${NOMINATIM_LIBDIR}/lib-python
                FILES_MATCHING PATTERN "*.py"
                PATTERN "paths.py" EXCLUDE
                PATTERN __pycache__ EXCLUDE)
        install(FILES ${PROJECT_BINARY_DIR}/paths-py.installed
                DESTINATION ${NOMINATIM_LIBDIR}/lib-python/${submodule}
                RENAME paths.py)
    endforeach()

    install(DIRECTORY lib-sql DESTINATION ${NOMINATIM_LIBDIR})

    install(FILES ${COUNTRY_GRID_FILE}
                  data/words.sql
            DESTINATION ${NOMINATIM_DATADIR})
endif()

if (BUILD_OSM2PGSQL)
    if (${CMAKE_VERSION} VERSION_LESS 3.13)
        # Installation of subdirectory targets was only introduced in 3.13.
        # So just copy the osm2pgsql file for older versions.
        install(PROGRAMS ${PROJECT_BINARY_DIR}/osm2pgsql/osm2pgsql
                DESTINATION ${NOMINATIM_LIBDIR})
    else()
        install(TARGETS osm2pgsql RUNTIME DESTINATION ${NOMINATIM_LIBDIR})
    endif()
endif()

install(FILES settings/env.defaults
              settings/address-levels.json
              settings/phrase-settings.json
              settings/import-admin.lua
              settings/import-street.lua
              settings/import-address.lua
              settings/import-full.lua
              settings/import-extratags.lua
              settings/flex-base.lua
              settings/icu_tokenizer.yaml
              settings/country_settings.yaml
        DESTINATION ${NOMINATIM_CONFIGDIR})

install(DIRECTORY settings/icu-rules
        DESTINATION ${NOMINATIM_CONFIGDIR})
install(DIRECTORY settings/country-names
        DESTINATION ${NOMINATIM_CONFIGDIR})

if (INSTALL_MUNIN_PLUGINS)
    install(FILES munin/nominatim_importlag
                  munin/nominatim_query_speed
                  munin/nominatim_requests
            DESTINATION ${NOMINATIM_MUNINDIR})
endif()

message(WARNING "Building with CMake is deprecated and will be removed in Nominatim 5.0."
                "Use Nominatim pip packages instead.\n"
                "See https://nominatim.org/release-docs/develop/admin/Installation/#downloading-and-building-nominatim")
