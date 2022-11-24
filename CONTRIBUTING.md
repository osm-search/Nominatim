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
 * indentation
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

The coding style is enforced with PHPCS and pylint. It can be tested with:

```
phpcs --report-width=120 --colors .
pylint3 --extension-pkg-whitelist=osmium nominatim
```

## Testing

Before submitting a pull request make sure that the tests pass:

```
  cd build
  make test
```

## Releases

Nominatim follows semantic versioning. Major releases are done for large changes
that require (or at least strongly recommend) a reimport of the databases.
Minor releases can usually be applied to exisiting databases Patch releases
contain bug fixes only and are released from a separate branch where the
relevant changes are cherry-picked from the master branch.

Checklist for releases:

* [ ] increase version in `nominatim/version.py` and CMakeLists.txt
* [ ] update `ChangeLog` (copy information from patch releases from release branch)
* [ ] complete `docs/admin/Migration.md`
* [ ] update EOL dates in `SECURITY.md`
* [ ] commit and make sure CI tests pass
* [ ] test migration
  * download, build and import previous version
  * migrate using master version
  * run updates using master version
* [ ] prepare tarball:
  * `git clone --recursive https://github.com/osm-search/Nominatim` (switch to right branch!)
  * `rm -r .git* osm2pgsql/.git*`
  * copy country data into `data/`
  * add version to base directory and package
* [ ] upload tarball to https://nominatim.org
* [ ] prepare documentation
  * check out new docs branch
  * change git checkout instructions to tarball download instructions or adapt version on existing ones
  * build documentation and copy to https://github.com/osm-search/nominatim-org-site
  * add new version to history
* [ ] check release tarball
  * download tarball as per new documentation instructions
  * compile and import Nominatim
  * run `nominatim --version` to confirm correct version
* [ ] tag new release and add a release on github.com
