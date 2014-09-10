ACLOCAL_AMFLAGS = -I osm2pgsql/m4
AUTOMAKE_OPTIONS = -Wno-portability

SUBDIRS = osm2pgsql module nominatim

NOMINATIM_SERVER ?= $(shell echo a | php -F lib/init.php -E 'echo CONST_Website_BaseURL."\n";')
NOMINATIM_DATABASE ?= $(shell echo a | php -F lib/init.php -E 'echo DB::parseDSN(CONST_Database_DSN)["database"];')

install:
	@echo Nominatim needs to be executed directly from this directory. No install necessary.

test:
	cd tests; NOMINATIM_SERVER=${NOMINATIM_SERVER} lettuce -t -Fail -t -poldi-only

test-fast:
	cd tests; NOMINATIM_SERVER=${NOMINATIM_SERVER} NOMINATIM_REUSE_TEMPLATE=1 lettuce -t -Fail -t -poldi-only

test-db:
	cd tests; NOMINATIM_SERVER=${NOMINATIM_SERVER} lettuce -t -Fail -t -poldi-only features/db

test-db-fast:
	cd tests; NOMINATIM_SERVER=${NOMINATIM_SERVER} NOMINATIM_REUSE_TEMPLATE=1 lettuce -t -Fail -t -poldi-only features/db

test-api:
	cd tests; NOMINATIM_SERVER=${NOMINATIM_SERVER} lettuce -t -Fail -t -poldi-only features/api

.PHONY: test test-fast test-db test-db-fast test-api
