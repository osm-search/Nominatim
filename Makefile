all:

# Building of wheels

build: clean-build build-db build-api

clean-build:
	rm -f dist/*

build-db:
	python3 -m build packaging/nominatim-db --outdir dist/

build-api:
	python3 -m build packaging/nominatim-api --outdir dist/

# Tests

tests: mypy lint pytest bdd

mypy:
	mypy --strict src

pytest:
	pytest test/python

lint:
	pylint src

bdd:
	cd test/bdd; behave -DREMOVE_TEMPLATE=1

# Documentation

doc:
	mkdocs build

serve-doc:
	mkdocs serve

.PHONY: tests mypy pytest lint bdd build clean-build build-db build-api doc serve-doc
