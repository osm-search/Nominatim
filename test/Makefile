all: bdd php
no-test-db: bdd-no-test-db php

bdd:
	cd bdd && behave -DREMOVE_TEMPLATE=1

icu:
	cd bdd && behave -DREMOVE_TEMPLATE=1 -DTOKENIZER=icu

php:
	cd php && phpunit ./

python:
	pytest python


.PHONY: bdd php no-test-db
