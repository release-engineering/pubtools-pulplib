# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- N/A

## [2.4.0] - 2020-01-13

### Added
- Introduced `Repository.search_content` API for retrieving content units
  from Pulp repositories.

### Fixed
- Fixed a bug that export an empty maintenance report would crash.
- Fixed another bug that maintenance report could have an invalid `last_updated_by` value.

## [2.3.1] - 2019-10-03

### Fixed
- Fixed certain exceptions from requests library not being propagated properly while
  getting maintenance report.

### Changed
- Task failure/completion logs now include task tags.
- Patterns to `Matcher.regex` are now more strictly typechecked when the matcher is created.

## [2.3.0] - 2019-09-25

### Added
- Introduced `Distributor.delete` for deleting a distributor from Pulp.

## [2.2.0] - 2019-09-16

### Added
- Introduced "proxy futures" for values produced by this library.
- Added a new attribute `relative_url` to `Distributor`, so users can search distributors
  by relative_url

## [2.1.0] - 2019-09-10

### Added
- A `search_distributor` API to search distributors on defined `Criteria`
- `Matcher.less_than()` matcher to find the results with fields less than
  the given value

### Fixed
- Fixed certain exceptions from requests library (such as SSL handshake errors) not being
  propagated correctly.

## [2.0.0] - 2019-09-09

### Added
- ``Page`` objects may now be directly used as iterables

### Changed
- **API break**: types of fields on model objects are now strictly validated
  during construction.
- **API break**: objects documented as immutable are now more deeply immutable;
  it is no longer possible to mutate list fields on these objects.
- **API break**: fixed inconsistencies on collection model fields. All fields
  previously declared as tuples have been updated to use (immutable) lists.

### Fixed
- **API break**: `MaintenanceReport.last_updated`, `MaintenanceEntry.started`
  are now `datetime` objects as documented. In previous versions, these were
  documented as datetimes but implemented as `str`.

### Deprecated
- ``Page.as_iter`` is now deprecated.

## [1.5.0] - 2019-09-03

### Added
- Introduced ``Repository.remove_content`` to remove contents of a repository.
- Introduced ``Unit`` classes representing various types of Pulp units.

### Fixed
- Fixed hashability of `PulpObject` subclasses, making it possible to use them
  in sets/dicts

### Deprecated
- ``Task.units_data`` is now deprecated in favor of ``Task.units``.

## [1.4.0] - 2019-09-02

### Added
- Support querying and updating maintenance mode of Pulp repositories
- Introduced ``Client.get_content_type_ids`` method to retrieve supported content types.

### Fixed
- Fixed a crash in `upload_file` when passed a file object opened in text mode

## [1.3.0] - 2019-08-15

### Added

- Introduced ``Repository.is_temporary`` attribute
- Extended search functionality; it is now possible to search using fields defined
  on the `PulpObject` classes. Searching on raw Pulp fields remains supported.

### Fixed
- Fixed inconsistency between real and fake clients: both clients now immediately raise
  if a search is attempted with invalid criteria.  Previously, the fake client would
  instead return a failed `Future`.

## [1.2.1] - 2019-08-12

### Fixed
- Fixed import conflicts for `pubtools` module

## [1.2.0] - 2019-08-07

### Added
- A new API `FileRepository.upload_file` to upload a file to Pulp repository

## [1.1.0] - 2019-07-03

### Added
- Extended search functionality to support matching fields by regular expression,
  using new `Matcher` class

### Deprecated
- `Criteria.exists` is now deprecated in favor of `Matcher.exists()`
- `Criteria.with_field_in` is now deprecated in favor of `Matcher.in_()`

## [1.0.0] - 2019-06-26

### Fixed
- Fixed some unstable autotests

### Changed
- Version set to 1.0.0 to indicate that API is now considered stable

## [0.3.0] - 2019-06-18

### Added
- Repository and Task objects have many additional attributes

### Changed
- Changed formatting of task error text; now includes a header with the ID of
  the failed task
- Client now stops paginated searches if the caller is not holding any references
  to the search result

### Fixed
- Fixed a crash on Python 2.6

## [0.2.1] - 2019-06-17

### Fixed
- Fixed various compatibility issues with old versions of libraries

## [0.2.0] - 2019-06-14

### Added
- Task error_summary and error_details are now initialized appropriately
  with data from Pulp
- Client now logs Pulp load every few minutes when awaiting tasks
- Client now logs warnings when Pulp operations are being retried
- Cancelling a future now attempts to cancel underlying Pulp task(s)
- Deleting a resource which is already nonexistent now succeeds

## [0.1.1] - 2019-06-13

### Fixed
- Fixed missing schema files from distribution

## 0.1.0 - 2019-06-13

- Initial release to PyPI

[Unreleased]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.4.0...HEAD
[2.4.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.3.1...v2.4.0
[2.3.1]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.3.0...v2.3.1
[2.3.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v1.5.0...v2.0.0
[1.5.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v1.2.1...v1.3.0
[1.2.1]: https://github.com/release-engineering/pubtools-pulplib/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/release-engineering/pubtools-pulplib/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/release-engineering/pubtools-pulplib/compare/v0.1.0...v0.1.1
