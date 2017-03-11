# Nominatim contribution guidelines

## Workflow

We operate the "Fork & Pull" model explained at

https://help.github.com/articles/using-pull-requests

You should fork the project into your own repo, create a topic branch
there and then make one or more pull requests back to the openstreetmap repository.
Your pull requests will then be reviewed and discussed.

## Coding style

Nominatim historically hasn't followed a particular coding style but we
are in process of consolodating the style. The following rules apply:

 * Python code uses the official Python style
 * indention
   * SQL use 2 spaces
   * all other file types use 4 spaces
   * [BSD style](https://en.wikipedia.org/wiki/Indent_style#Allman_style) for braces
 * spaces
   * spaces before and after equal signs and operators
   * no trailing spaces
   * no spaces after opening and before closing bracket
   * leave out space between a function name and bracket
     but add one between control statement(if, while, etc.) and bracket

The coding style is enforced with PHPCS and can be tested with:

```
  phpcs --report-width=120 --colors */**.php
```

## Testing

Before submitting a pull request make sure that the following tests pass:

```
  cd test/bdd
  behave -DBUILDDIR=<builddir> db osm2pgsql
```

```
  cd test/php
  phpunit ./
```
