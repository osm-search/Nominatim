# just use the pgxs makefile
ADD_CUSTOM_COMMAND( OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/dummy
        COMMAND PGXS=${PGXS} PG_CONFIG=${PG_CONFIG} MODSRCDIR=${CMAKE_CURRENT_SOURCE_DIR} $(MAKE) -f ${CMAKE_CURRENT_SOURCE_DIR}/Makefile
        COMMENT "Running external makefile ${PGXS}"
        )

ADD_CUSTOM_TARGET( nominatim_lib ALL
        DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/dummy
        )

