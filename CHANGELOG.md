# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- n/a

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

[Unreleased]: https://github.com/release-engineering/pubtools-pulplib/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/release-engineering/pubtools-pulplib/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/release-engineering/pubtools-pulplib/compare/v0.1.0...v0.1.1
