all: bdd php

bdd:
	cd bdd && behave -DREMOVE_TEMPLATE=1

php:
	cd php && phpunit ./

.PHONY: bdd php
