# Auto-generated vagrant install documentation


# build the actual documentation

configure_file(mkdocs.yml ../mkdocs.yml)
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/appendix)
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/data-sources)

ADD_CUSTOM_TARGET(doc
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${CMAKE_CURRENT_SOURCE_DIR}/admin ${CMAKE_CURRENT_BINARY_DIR}/admin
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${CMAKE_CURRENT_SOURCE_DIR}/develop ${CMAKE_CURRENT_BINARY_DIR}/develop
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${CMAKE_CURRENT_SOURCE_DIR}/api ${CMAKE_CURRENT_BINARY_DIR}/api
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${CMAKE_CURRENT_SOURCE_DIR}/index.md ${CMAKE_CURRENT_BINARY_DIR}/index.md
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${CMAKE_CURRENT_SOURCE_DIR}/extra.css ${CMAKE_CURRENT_BINARY_DIR}/extra.css
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${CMAKE_CURRENT_SOURCE_DIR}/data-sources/overview.md ${CMAKE_CURRENT_BINARY_DIR}/data-sources/overview.md
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${PROJECT_SOURCE_DIR}/data-sources/us-tiger/README.md ${CMAKE_CURRENT_BINARY_DIR}/data-sources/US-Tiger.md
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${PROJECT_SOURCE_DIR}/data-sources/gb-postcodes/README.md ${CMAKE_CURRENT_BINARY_DIR}/data-sources/GB-Postcodes.md
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${PROJECT_SOURCE_DIR}/data-sources/country-grid/README.md ${CMAKE_CURRENT_BINARY_DIR}/data-sources/Country-Grid.md
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${PROJECT_SOURCE_DIR}/data-sources/country-grid/mexico.quad.png ${CMAKE_CURRENT_BINARY_DIR}/data-sources/mexico.quad.png
   COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/bash2md.sh ${PROJECT_SOURCE_DIR}/vagrant/Install-on-Centos-7.sh ${CMAKE_CURRENT_BINARY_DIR}/appendix/Install-on-Centos-7.md
   COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/bash2md.sh ${PROJECT_SOURCE_DIR}/vagrant/Install-on-Ubuntu-16.sh ${CMAKE_CURRENT_BINARY_DIR}/appendix/Install-on-Ubuntu-16.md
   COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/bash2md.sh ${PROJECT_SOURCE_DIR}/vagrant/Install-on-Ubuntu-18.sh ${CMAKE_CURRENT_BINARY_DIR}/appendix/Install-on-Ubuntu-18.md
   COMMAND mkdocs build -d ${CMAKE_CURRENT_BINARY_DIR}/../site-html -f ${CMAKE_CURRENT_BINARY_DIR}/../mkdocs.yml
)


