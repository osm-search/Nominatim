# Auto-generated vagrant install documentation


# build the actual documentation

configure_file(mkdocs.yml ../mkdocs.yml)
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/appendix)

set (DOC_SOURCES
     admin
     develop
     api
     customize
     library
     index.md
     extra.css
     styles.css
    )

foreach (src ${DOC_SOURCES})
    execute_process(
        COMMAND ${CMAKE_COMMAND} -E create_symlink ${CMAKE_CURRENT_SOURCE_DIR}/${src} ${CMAKE_CURRENT_BINARY_DIR}/${src}
    )
endforeach()

ADD_CUSTOM_TARGET(doc
   COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/bash2md.sh ${PROJECT_SOURCE_DIR}/vagrant/Install-on-Ubuntu-24.sh ${CMAKE_CURRENT_BINARY_DIR}/appendix/Install-on-Ubuntu-24.md
   COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/bash2md.sh ${PROJECT_SOURCE_DIR}/vagrant/Install-on-Ubuntu-22.sh ${CMAKE_CURRENT_BINARY_DIR}/appendix/Install-on-Ubuntu-22.md
   COMMAND mkdocs build -d ${CMAKE_CURRENT_BINARY_DIR}/../site-html -f ${CMAKE_CURRENT_BINARY_DIR}/../mkdocs.yml
)

ADD_CUSTOM_TARGET(serve-doc
    COMMAND mkdocs serve -f ${CMAKE_CURRENT_BINARY_DIR}/../mkdocs.yml
    WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
)
