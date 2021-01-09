# Nominatim contribution guidelines

## Reporting Bugs

Bugs can be reported at https://github.com/openstreetmap/Nominatim/issues.
Please always open a separate issue for each problem. In particular, do
not add your bugs to closed issues. They may looks similar to you but
often are completely different from the maintainer's point of view.

## Workflow for Pull Requests

We love to get pull requests from you. We operate the "Fork & Pull" model
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
are in process of consolidating the style. The following rules apply:

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
 * for PHP variables use CamelCase with a prefixing letter indicating the type
   (i - integer, f - float, a - array, s - string, o - object)

The coding style is enforced with PHPCS and can be tested with:

```
  phpcs --report-width=120 --colors .
```

## Testing

Before submitting a pull request make sure that the tests pass:

```
  cd build
  make test
```
