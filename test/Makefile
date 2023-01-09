all: bdd php python
no-test-db: bdd-no-test-db php

bdd:
	cd bdd && behave -DREMOVE_TEMPLATE=1

php:
	cd php && phpunit ./

python:
	pytest python


.PHONY: bdd php no-test-db python
