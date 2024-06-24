all:

# Building of wheels

build: build-core build-db build-api

build-core:
	python3 -m build packaging/nominatim-core --outdir dist/

build-db:
	python3 -m build packaging/nominatim-db --outdir dist/

build-api:
	python3 -m build packaging/nominatim-api --outdir dist/

# Tests

tests: mypy lint pytest

mypy:
	mypy --strict src

pytest:
	pytest test/python

lint:
	pylint src

bdd:
	cd test/bdd; behave -DREMOVE_TEMPLATE=1

.PHONY: tests mypy pytest lint bdd build build-core build-db build-api
