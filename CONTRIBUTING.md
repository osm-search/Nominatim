# Nominatim contribution guidelines

## Reporting Bugs

Bugs can be reported at https://github.com/openstreetmap/Nominatim/issues.
Please always open a separate issue for each problem. In particular, do
not add your bugs to closed issues. They may look similar to you but
often are completely different from the maintainer's point of view.

## Workflow for Pull Requests

We love to get pull requests from you. We operate the "Fork & Pull" model
explained at

https://help.github.com/articles/using-pull-requests

You should fork the project into your own repo, create a topic branch
there and then make a single pull requests back to the main repository.
Your pull requests will then be reviewed and discussed.

Please make sure to follow these guidelines:

* Make sure CI passes _before_ opening the pull request. The repo is configured
  to run the CI on branches. Once you have enabled the CI on your forked
  repo, Actions will execute every time you push to your branch. Check
  the Actions tab in your repo to make sure everything works.
* Make sure that you have time to react to these comments and amend the code or
  engage in a conversation. Do not expect that others will pick up your code,
  it will almost never happen.
* Open a separate pull request for each issue you want to address.
  Don't mix multiple changes. In particular, don't mix style cleanups with
  feature pull requests (exceptions, see 'Style modernisation' below).
* For small fixes and amendments open a PR directly.
  If you plan to make larger changes, please open an issue first or comment
  on the appropriate issue to outline your planned implementation.

### Using AI-assisted code generators

PRs that include AI-generated content, may that be in code, in the PR
description or in documentation need to

1. clearly mark the AI-generated sections as such, for example, by
   mentioning all use of AI in the PR description, and
2. include proof that you have run the generated code on an actual
   installation of Nominatim. Adding and executing tests will not be
   sufficient. You need to show that the code actually solves the problem
   the PR claims to solve.

## Getting Started with Development

Please see the development section of the Nominatim documentation for

* [an architecture overview](https://nominatim.org/release-docs/develop/develop/overview/)
  and backgrounds on some of the algorithms
* [how to set up a development environment](https://nominatim.org/release-docs/develop/develop/Development-Environment/)
* and background on [how tests are organised](https://nominatim.org/release-docs/develop/develop/Testing/)


## Coding style

The coding style for Python is enforced with flake8. It can be tested with:

```
make lint
```

SQL code is currently not linted but should follow the following rules:

* 2 spaces indentation
* UPPER CASE for all SQL keywords

### Style modernisation

There are a few places where we modernize code style as we go. The following
changes can be made when you touch the code anyway:

* update copyright date in the file header to the current year
* switch Python code to use [generics in standard collections](https://docs.python.org/3/whatsnew/3.9.html#type-hinting-generics-in-standard-collections)

## Testing

Before submitting a pull request make sure that the tests pass:

```
  make tests
```

## Releases

Nominatim follows semantic versioning. Major releases are done for large changes
that require (or at least strongly recommend) a reimport of the databases.
Minor releases can usually be applied to existing databases. Patch releases
contain bug fixes only and are released from a separate branch where the
relevant changes are cherry-picked from the master branch.

Checklist for releases:

* [ ] increase versions in
  * `src/nominatim_api/version.py`
  * `src/nominatim_db/version.py`
* [ ] update `ChangeLog` (copy information from patch releases from release branch)
* [ ] complete `docs/admin/Migration.md`
* [ ] update EOL dates in `SECURITY.md`
* [ ] commit and make sure CI tests pass
* [ ] update OSMF production repo and release new version -post1 there
* [ ] test migration
  * download, build and import previous version
  * migrate using master version
  * run updates using master version
* [ ] prepare tarball:
  * `git clone https://github.com/osm-search/Nominatim` (switch to right branch!)
  * `rm -r .git*`
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
* [ ] build pip packages and upload to pypi
  * `make build`
  * `twine upload dist/*`
