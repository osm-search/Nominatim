# SYNOPSIS
#
#   AX_LIB_POSTGRESQL_SVR([MINIMUM-VERSION])
#
# DESCRIPTION
#
#   This macro provides tests of availability of PostgreSQL server library
#
#   This macro calls:
#
#     AC_SUBST(POSTGRESQL_PGXS)
#     AC_SUBST(POSTGRESQL_SERVER_CFLAGS)
#
# LICENSE
#
#   Copyright (c) 2008 Mateusz Loskot <mateusz@loskot.net>
#   Copyright (c) 2015 Sarah Hoffmann <lonia@denofr.de>
#
#   Copying and distribution of this file, with or without modification, are
#   permitted in any medium without royalty provided the copyright notice
#   and this notice are preserved.

AC_DEFUN([AX_LIB_POSTGRESQL_SVR],
[
    AC_ARG_WITH([postgresql],
        AC_HELP_STRING([--with-postgresql-svr=@<:@ARG@:>@],
            [use PostgreSQL server library @<:@default=yes@:>@, optionally specify path to pg_config]
        ),
        [
        if test "$withval" = "no"; then
            want_postgresql="no"
        elif test "$withval" = "yes"; then
            want_postgresql="yes"
        else
            want_postgresql="yes"
            PG_CONFIG="$withval"
        fi
        ],
        [want_postgresql="yes"]
    )

    dnl
    dnl Check PostgreSQL server libraries
    dnl

    if test "$want_postgresql" = "yes"; then

        if test -z "$PG_CONFIG" -o test; then
            AC_PATH_PROG([PG_CONFIG], [pg_config], [])
        fi

        if test ! -x "$PG_CONFIG"; then
            AC_MSG_ERROR([$PG_CONFIG does not exist or it is not an exectuable file])
            PG_CONFIG="no"
            found_postgresql="no"
        fi

        if test "$PG_CONFIG" != "no"; then
            AC_MSG_CHECKING([for PostgreSQL server libraries])

            POSTGRESQL_SERVER_CFLAGS="-I`$PG_CONFIG --includedir-server`"

            POSTGRESQL_VERSION=`$PG_CONFIG --version | sed -e 's#PostgreSQL ##'`

            POSTGRESQL_PGXS=`$PG_CONFIG --pgxs`
        if test -f "$POSTGRESQL_PGXS"
        then
          found_postgresql="yes"
              AC_MSG_RESULT([yes])
        fi
        else
            found_postgresql="no"
            AC_MSG_RESULT([no])
        fi
    fi

    dnl
    dnl Check if required version of PostgreSQL is available
    dnl


    postgresql_version_req=ifelse([$1], [], [], [$1])

    if test "$found_postgresql" = "yes" -a -n "$postgresql_version_req"; then

        AC_MSG_CHECKING([if PostgreSQL version is >= $postgresql_version_req])

        dnl Decompose required version string of PostgreSQL
        dnl and calculate its number representation
        postgresql_version_req_major=`expr $postgresql_version_req : '\([[0-9]]*\)'`
        postgresql_version_req_minor=`expr $postgresql_version_req : '[[0-9]]*\.\([[0-9]]*\)'`
        postgresql_version_req_micro=`expr $postgresql_version_req : '[[0-9]]*\.[[0-9]]*\.\([[0-9]]*\)'`
        if test "x$postgresql_version_req_micro" = "x"; then
            postgresql_version_req_micro="0"
        fi

        postgresql_version_req_number=`expr $postgresql_version_req_major \* 1000000 \
                                   \+ $postgresql_version_req_minor \* 1000 \
                                   \+ $postgresql_version_req_micro`

        dnl Decompose version string of installed PostgreSQL
        dnl and calculate its number representation
        postgresql_version_major=`expr $POSTGRESQL_VERSION : '\([[0-9]]*\)'`
        postgresql_version_minor=`expr $POSTGRESQL_VERSION : '[[0-9]]*\.\([[0-9]]*\)'`
        postgresql_version_micro=`expr $POSTGRESQL_VERSION : '[[0-9]]*\.[[0-9]]*\.\([[0-9]]*\)'`
        if test "x$postgresql_version_micro" = "x"; then
            postgresql_version_micro="0"
        fi

        postgresql_version_number=`expr $postgresql_version_major \* 1000000 \
                                   \+ $postgresql_version_minor \* 1000 \
                                   \+ $postgresql_version_micro`

        postgresql_version_check=`expr $postgresql_version_number \>\= $postgresql_version_req_number`
        if test "$postgresql_version_check" = "1"; then
            AC_MSG_RESULT([yes])
        else
            AC_MSG_RESULT([no])
        fi
    fi

    AC_SUBST([POSTGRESQL_PGXS])
    AC_SUBST([POSTGRESQL_SERVER_CFLAGS])
])

