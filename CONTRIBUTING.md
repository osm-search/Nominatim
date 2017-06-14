# Nominatim contribution guidelines

## Reporting Bugs

Bugs can be reported at https://github.com/openstreetmap/Nominatim/issues.
Please always open a separate issue for each problem. In particular, do
not add your bugs to closed issues. They may looks similar to you but
often are completely different from the maintainer's point of view.

### When Reporting Bad Search Results...

Please make sure to add the following information:

 * the URL of the query that produces the bad result
 * the result you are getting
 * the expected result, preferably a link to the OSM object you want to find,
   otherwise an address that is as precise as possible
 
 To get the link to the OSM object, you can try the following:
 
 * go to https://openstreetmap.org
 * zoom to the area of the map where you expect the result and
   zoom in as much as possible
 * click on the question mark on the right side of the map,
   then with the queston cursor on the map where your object is located
 * find the object of interest in the list that appears on the left side
 * click on the object and report the URL back that the browser shows

### When Reporting Problems with your Installation...

Please add the following information to your issue:

 * hardware configuration: RAM size, CPUs, kind and size of disks
 * Operating system (also mention if you are running on a cloud service)
 * Postgres and Postgis version
 * list of settings you changed in your Postgres configuration
 * Nominatim version (release version or,
   if you run from the git repo, the output of `git rev-parse HEAD`)
 * (if applicable) exact command line of the command that was causing the issue


## Workflow for Pull Requests

We love to get pull reuqests from you. We operate the "Fork & Pull" model
explained at

https://help.github.com/articles/using-pull-requests

You should fork the project into your own repo, create a topic branch
there and then make one or more pull requests back to the openstreetmap repository.
Your pull requests will then be reviewed and discussed. Please be aware
that you are responsible for your pull requests. You should be prepared
to get change requests because as the maintainers we have to make sure
that your contribution fits well with the rest of the code. Please make
sure that you have time to react to these comments and amend the code or
engage in a conversion. Do not expect that others will pick up your code,
it will almost never happen.

Please open a separate pull request for each issue you want to address.
Don't mix multiple changes. In particular, don't mix style cleanups with
feature pull requests. If you plan to make larger changes, please open
an issue first or comment on the appropriate issue already existing so
that duplicate work can be avoided.

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
