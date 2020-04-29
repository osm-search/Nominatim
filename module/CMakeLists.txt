# just use the pgxs makefile
find_program(PG_CONFIG pg_config)
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

