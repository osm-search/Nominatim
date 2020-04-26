# Auto-generated vagrant install documentation


# build the actual documentation

configure_file(mkdocs.yml ../mkdocs.yml)
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/appendix)
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/data-sources)

set (DOC_SOURCES
     admin
     develop
     api
     index.md
     extra.css
     styles.css
     data-sources/overview.md
    )

foreach (src ${DOC_SOURCES})
    execute_process(
        COMMAND ${CMAKE_COMMAND} -E create_symlink ${CMAKE_CURRENT_SOURCE_DIR}/${src} ${CMAKE_CURRENT_BINARY_DIR}/${src}
    )
endforeach()

execute_process(
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${PROJECT_SOURCE_DIR}/data-sources/us-tiger/README.md ${CMAKE_CURRENT_BINARY_DIR}/data-sources/US-Tiger.md
)
execute_process(
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${PROJECT_SOURCE_DIR}/data-sources/gb-postcodes/README.md ${CMAKE_CURRENT_BINARY_DIR}/data-sources/GB-Postcodes.md
)
execute_process(
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${PROJECT_SOURCE_DIR}/data-sources/country-grid/README.md ${CMAKE_CURRENT_BINARY_DIR}/data-sources/Country-Grid.md
)
execute_process(
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${PROJECT_SOURCE_DIR}/data-sources/country-grid/mexico.quad.png ${CMAKE_CURRENT_BINARY_DIR}/data-sources/mexico.quad.png
)
execute_process(
   COMMAND ${CMAKE_COMMAND} -E create_symlink ${PROJECT_SOURCE_DIR}/data-sources/wikipedia-wikidata/README.md  ${CMAKE_CURRENT_BINARY_DIR}/data-sources/Wikipedia-Wikidata.md
)

ADD_CUSTOM_TARGET(doc
   COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/bash2md.sh ${PROJECT_SOURCE_DIR}/vagrant/Install-on-Centos-7.sh ${CMAKE_CURRENT_BINARY_DIR}/appendix/Install-on-Centos-7.md
   COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/bash2md.sh ${PROJECT_SOURCE_DIR}/vagrant/Install-on-Ubuntu-16.sh ${CMAKE_CURRENT_BINARY_DIR}/appendix/Install-on-Ubuntu-16.md
   COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/bash2md.sh ${PROJECT_SOURCE_DIR}/vagrant/Install-on-Ubuntu-18.sh ${CMAKE_CURRENT_BINARY_DIR}/appendix/Install-on-Ubuntu-18.md
   COMMAND mkdocs build -d ${CMAKE_CURRENT_BINARY_DIR}/../site-html -f ${CMAKE_CURRENT_BINARY_DIR}/../mkdocs.yml
)


