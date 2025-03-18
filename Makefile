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
	mypy --strict --python-version 3.8 src

pytest:
	pytest test/python

lint:
	flake8 src test/python test/bdd

bdd:
	pytest test/bdd
	cd test/bdd; behave -DREMOVE_TEMPLATE=1 db osm2pgsql

# Documentation

doc:
	mkdocs build

serve-doc:
	mkdocs serve

manpage:
	argparse-manpage --pyfile man/create-manpage.py --function get_parser --project-name Nominatim --url https://nominatim.org  > man/nominatim.1 --author 'the Nominatim developer community' --author-email info@nominatim.org


.PHONY: tests mypy pytest lint bdd build clean-build build-db build-api doc serve-doc manpage
