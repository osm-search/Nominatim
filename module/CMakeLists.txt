# just use the pgxs makefile

foreach(suffix ${PostgreSQL_ADDITIONAL_VERSIONS} "14" "13" "12" "11" "10" "9.6")
    list(APPEND PG_CONFIG_HINTS
         "/usr/pgsql-${suffix}/bin")
endforeach()

find_program(PG_CONFIG pg_config HINTS ${PG_CONFIG_HINTS})



execute_process(COMMAND ${PG_CONFIG} --pgxs
            OUTPUT_VARIABLE PGXS
            OUTPUT_STRIP_TRAILING_WHITESPACE)

if (NOT EXISTS "${PGXS}")
message(FATAL_ERROR "Postgresql server package not found.")
endif()

ADD_CUSTOM_COMMAND( OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/dummy
        COMMAND PGXS=${PGXS} PG_CONFIG=${PG_CONFIG} MODSRCDIR=${CMAKE_CURRENT_SOURCE_DIR} $(MAKE) -f ${CMAKE_CURRENT_SOURCE_DIR}/Makefile
        COMMENT "Running external makefile ${PGXS}"
        )

ADD_CUSTOM_TARGET( nominatim_lib ALL
        DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/dummy
        )

