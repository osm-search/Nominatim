# Auto-generated vagrant install documentation


# build the actual documentation

configure_file(mkdocs.yml ../mkdocs.yml)
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/appendix)

ADD_CUSTOM_TARGET(doc
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${CMAKE_CURRENT_SOURCE_DIR}/admin ${CMAKE_CURRENT_BINARY_DIR}/admin
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${CMAKE_CURRENT_SOURCE_DIR}/index.md ${CMAKE_CURRENT_BINARY_DIR}/index.md
   COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/bash2md.sh ${PROJECT_SOURCE_DIR}/vagrant/Install-on-Centos-7.sh ${CMAKE_CURRENT_BINARY_DIR}/appendix/Install-on-Centos-7.md
   COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/bash2md.sh ${PROJECT_SOURCE_DIR}/vagrant/Install-on-Ubuntu-16.sh ${CMAKE_CURRENT_BINARY_DIR}/appendix/Install-on-Ubuntu-16.md
   COMMAND mkdocs build -d ${CMAKE_CURRENT_BINARY_DIR}/../site-html -f ${CMAKE_CURRENT_BINARY_DIR}/../mkdocs.yml
)


