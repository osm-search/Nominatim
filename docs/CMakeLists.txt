# Auto-generated vagrant install documentation

set (INSTALLDOCFILES
     install-on-centos-7
    )

foreach (df ${INSTALLDOCFILES})
    ADD_CUSTOM_COMMAND( OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${df}.md
        COMMAND sed [=['/^#!/d;s:^#\( \|$$\)::;s/.*#DOCS://']=] ${PROJECT_SOURCE_DIR}/vagrant/${df}.sh > ${CMAKE_CURRENT_BINARY_DIR}/${df}.md
        MAIN_DEPENDENCY ${PROJECT_SOURCE_DIR}/vagrant/${df}.sh
        COMMENT "Creating markdown docs from vagrant/${df}.sh"
        )

ADD_CUSTOM_TARGET( md_install_${df} ALL
        DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/${df}.md
        )
endforeach()

