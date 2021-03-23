# Creates and installs manual page

execute_process(
    COMMAND ${CMAKE_COMMAND} -E create_symlink ${CMAKE_CURRENT_SOURCE_DIR}/nominatim.1 ${CMAKE_CURRENT_BINARY_DIR}/nominatim.1
)

configure_file(${PROJECT_SOURCE_DIR}/manual/create-manpage.tmpl create_manpage.py)

find_program(ARGPARSEMANPAGE argparse-manpage)

ADD_CUSTOM_TARGET(manpage
    COMMAND ${ARGPARSEMANPAGE} --pyfile ${CMAKE_CURRENT_BINARY_DIR}/create_manpage.py --function get_parser > nominatim.1
)

install(FILES ${CMAKE_CURRENT_BINARY_DIR}/nominatim.1 DESTINATION share/man/man1 )
