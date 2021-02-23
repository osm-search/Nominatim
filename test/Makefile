all: bdd php
no-test-db: bdd-no-test-db php

bdd:
	cd bdd && behave -DREMOVE_TEMPLATE=1

bdd-no-test-db:
	cd bdd && behave -DREMOVE_TEMPLATE=1 db osm2pgsql

php:
	cd php && phpunit ./

python:
	pytest python


.PHONY: bdd php no-test-db
