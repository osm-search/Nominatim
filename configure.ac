AC_INIT(Nominatim,2.4)
if git rev-parse HEAD 2>/dev/null >/dev/null; then
    AC_SUBST([PACKAGE_VERSION], [$PACKAGE_VERSION-git-`git rev-parse --short HEAD`])
fi

dnl Required autoconf version
AC_PREREQ(2.61)

AM_INIT_AUTOMAKE([1.9.6 dist-bzip2 std-options check-news])

dnl Additional macro definitions are in here
AC_CONFIG_MACRO_DIR([osm2pgsql/m4])

dnl Generate configuration header file
AC_CONFIG_HEADER(nominatim/config.h)


dnl Find C compiler
AC_PROG_CC

dnl Find C++ compiler
AC_PROG_CXX

dnl pthread
AX_PTHREAD([], [AC_MSG_ERROR([pthread library required])])

dnl Check for Geos library
AX_LIB_GEOS
if test "x$GEOS_VERSION" = "x" 
then
  AC_MSG_ERROR([required library not found]);
fi

dnl Check for Proj library
AX_LIB_PROJ
if test "$HAVE_PROJ" = "no" 
then
  AC_MSG_ERROR([required library not found]);
fi


dnl Check for PostgresSQL client library
AX_LIB_POSTGRESQL(9.0)
if test "x$POSTGRESQL_VERSION" = "x"
then
    AC_MSG_ERROR([postgresql client library not found])
fi
if test ! -f "$POSTGRESQL_PGXS"
then
    AC_MSG_ERROR([postgresql server development library not found])
fi

dnl Check for bzip2 library
AX_LIB_BZIP2
if test "$HAVE_BZIP2" = "no" 
then
  AC_MSG_ERROR([required library not found]);
fi

dnl Check for libxml2 library
AM_PATH_XML2

AC_CONFIG_SUBDIRS([osm2pgsql])

AC_OUTPUT(Makefile nominatim/Makefile module/Makefile)
