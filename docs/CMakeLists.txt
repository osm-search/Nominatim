# Auto-generated vagrant install documentation

set (INSTALLDOCFILES
     Install-on-Centos-7
     Install-on-Ubuntu-16
    )

foreach (df ${INSTALLDOCFILES})
    ADD_CUSTOM_COMMAND( OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${df}.md
        COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/bash2md.sh ${PROJECT_SOURCE_DIR}/vagrant/${df}.sh ${CMAKE_CURRENT_BINARY_DIR}/${df}.md
        MAIN_DEPENDENCY ${PROJECT_SOURCE_DIR}/vagrant/${df}.sh
        DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/bash2md.sh
        COMMENT "Creating markdown docs from vagrant/${df}.sh"
        )

ADD_CUSTOM_TARGET( md_install_${df} ALL
        DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/${df}.md
        )
endforeach()

# Copied static documentation

set (GENERALDOCFILES
     Installation.md
     Import-and-Update.md
     Faq.md
    )

foreach (df ${GENERALDOCFILES})
   CONFIGURE_FILE(${df} ${df})
endforeach()

