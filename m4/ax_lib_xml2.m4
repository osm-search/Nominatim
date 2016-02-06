# SYNOPSIS
#
#   AX_LIB_XML2([MINIMUM-VERSION])
#
# DESCRIPTION
#
#   This macro provides tests of availability of xml2 'libxml2' library
#   of particular version or newer.
#
#   AX_LIB_LIBXML2 macro takes only one argument which is optional. If
#   there is no required version passed, then macro does not run version
#   test.
#
#   The --with-libxml2 option takes one of three possible values:
#
#   no - do not check for xml2 library
#
#   yes - do check for xml2 library in standard locations (xml2-config
#   should be in the PATH)
#
#   path - complete path to xml2-config utility, use this option if xml2-config
#   can't be found in the PATH
#
#   This macro calls:
#
#     AC_SUBST(XML2_CFLAGS)
#     AC_SUBST(XML2_LDFLAGS)
#     AC_SUBST(XML2_VERSION)
#
#   And sets:
#
#     HAVE_XML2
#
# LICENSE
#
#   Copyright (c) 2009 Hartmut Holzgraefe <hartmut@php.net>
#
#   Copying and distribution of this file, with or without modification, are
#   permitted in any medium without royalty provided the copyright notice
#   and this notice are preserved.

AC_DEFUN([AX_LIB_XML2],
[
    AC_ARG_WITH([libxml2],
        AC_HELP_STRING([--with-libxml2=@<:@ARG@:>@],
            [use libxml2 library @<:@default=yes@:>@, optionally specify path to xml2-config]
        ),
        [
        if test "$withval" = "no"; then
            want_libxml2="no"
        elif test "$withval" = "yes"; then
            want_libxml2="yes"
        else
            want_libxml2="yes"
            XML2_CONFIG="$withval"
        fi
        ],
        [want_libxml2="yes"]
    )

    XML2_CFLAGS=""
    XML2_LDFLAGS=""
    XML2_VERSION=""

    dnl
    dnl Check xml2 libraries (libxml2)
    dnl

    if test "$want_libxml2" = "yes"; then

        if test -z "$XML2_CONFIG" -o test; then
            AC_PATH_PROG([XML2_CONFIG], [xml2-config], [])
        fi

        if test ! -x "$XML2_CONFIG"; then
            AC_MSG_ERROR([$XML2_CONFIG does not exist or it is not an exectuable file])
            XML2_CONFIG="no"
            found_libxml2="no"
        fi

        if test "$XML2_CONFIG" != "no"; then
            AC_MSG_CHECKING([for xml2 libraries])

            XML2_CFLAGS="`$XML2_CONFIG --cflags`"
            XML2_LDFLAGS="`$XML2_CONFIG --libs`"

            XML2_VERSION=`$XML2_CONFIG --version`

            AC_DEFINE([HAVE_XML2], [1],
                [Define to 1 if xml2 libraries are available])

            found_libxml2="yes"
            AC_MSG_RESULT([yes])
        else
            found_libxml2="no"
            AC_MSG_RESULT([no])
        fi
    fi

    dnl
    dnl Check if required version of xml2 is available
    dnl


    libxml2_version_req=ifelse([$1], [], [], [$1])


    if test "$found_libxml2" = "yes" -a -n "$libxml2_version_req"; then

        AC_MSG_CHECKING([if libxml2 version is >= $libxml2_version_req])

        dnl Decompose required version string of libxml2
        dnl and calculate its number representation
        libxml2_version_req_major=`expr $libxml2_version_req : '\([[0-9]]*\)'`
        libxml2_version_req_minor=`expr $libxml2_version_req : '[[0-9]]*\.\([[0-9]]*\)'`
        libxml2_version_req_micro=`expr $libxml2_version_req : '[[0-9]]*\.[[0-9]]*\.\([[0-9]]*\)'`
        if test "x$libxml2_version_req_micro" = "x"; then
            libxml2_version_req_micro="0"
        fi

        libxml2_version_req_number=`expr $libxml2_version_req_major \* 1000000 \
                                   \+ $libxml2_version_req_minor \* 1000 \
                                   \+ $libxml2_version_req_micro`

        dnl Decompose version string of installed PostgreSQL
        dnl and calculate its number representation
        libxml2_version_major=`expr $XML2_VERSION : '\([[0-9]]*\)'`
        libxml2_version_minor=`expr $XML2_VERSION : '[[0-9]]*\.\([[0-9]]*\)'`
        libxml2_version_micro=`expr $XML2_VERSION : '[[0-9]]*\.[[0-9]]*\.\([[0-9]]*\)'`
        if test "x$libxml2_version_micro" = "x"; then
            libxml2_version_micro="0"
        fi

        libxml2_version_number=`expr $libxml2_version_major \* 1000000 \
                                   \+ $libxml2_version_minor \* 1000 \
                                   \+ $libxml2_version_micro`

        libxml2_version_check=`expr $libxml2_version_number \>\= $libxml2_version_req_number`
        if test "$libxml2_version_check" = "1"; then
            AC_MSG_RESULT([yes])
        else
            AC_MSG_RESULT([no])
        fi
    fi

    AC_SUBST([XML2_VERSION])
    AC_SUBST([XML2_CFLAGS])
    AC_SUBST([XML2_LDFLAGS])
])

