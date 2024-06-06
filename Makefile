all:

# Building of wheels

build: build-core build-db build-api

build-core:
	cd packaging/nominatim-core; python3 -m build . --outdir ../dist/

build-db:
	cd packaging/nominatim-db; python3 -m build . --outdir ../dist/

build-api:
	cd packaging/nominatim-api; python3 -m build . --outdir ../dist/

# Tests

tests: mypy lint pytest

mypy:
	python3 -m mypy --strict src

pytest:
	python3 -m pytest test/python

lint:
	python3 -m pylint src

bdd:
	cd test/bdd; behave -DREMOVE_TEMPLATE=1

.PHONY: tests mypy pytest lint bdd build build-core build-db build-api
