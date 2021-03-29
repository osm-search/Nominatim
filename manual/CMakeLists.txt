# Creates and installs manual page

configure_file(${PROJECT_SOURCE_DIR}/manual/create-manpage.tmpl create_manpage.py)

find_program(ARGPARSEMANPAGE argparse-manpage)

ADD_CUSTOM_TARGET(manpage
    COMMAND ${ARGPARSEMANPAGE} --pyfile ${CMAKE_CURRENT_BINARY_DIR}/create_manpage.py
    --function get_parser --project-name Nominatim
    --url https://nominatim.org  > ${CMAKE_CURRENT_SOURCE_DIR}/nominatim.1

    COMMAND sed -i '/.SH AUTHORS/I,+2 d' ${CMAKE_CURRENT_SOURCE_DIR}/nominatim.1
)

install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/nominatim.1 DESTINATION share/man/man1 )
