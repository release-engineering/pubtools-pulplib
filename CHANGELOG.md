# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- n/a

## [2.30.0] - 2022-04-04

- Fixed searches in progress sometimes incorrectly cancelled during pagination

## [2.29.0] - 2022-03-28

- Fixed upload of RPMs with versionless dependencies via fake client
- Fixed `repr` for `RpmDependency`
- Added fields to repository model: `arch`, `platform_full_version`, `product_versions`
- Added `update_repository` method to update a repository's mutable fields
- Added `CopyOptions` for `copy_content` method

## [2.28.1] - 2022-03-16

- Fixed a deprecation warning logged during upload of comps.xml.

## [2.28.0] - 2022-03-15

- Added `criteria` to `Repository.remove_content`.
- Fixed handling of absent `default` fields in package environment options during
  upload of comps.xml.

## [2.27.0] - 2022-03-10

- Pulp objects have an improved `repr` implementation which omits redundant information.
- `TaskFailedException` now includes task failure details in the exception's message.
- `YumRepository.get_(debug|binary|source)_repository` have been revised to use
  distributor config rather than repo config. This allows the methods to work on the
  fake client.

## [2.26.1] - 2022-03-09

- Add a workaround for Python 2 strptime bug [7980](https://bugs.python.org/issue7980).

## [2.26.0] - 2022-03-08

- Make most model classes slotted, for reduced memory usage.

## [2.25.1] - 2022-03-02

- Make `humanize` dependency, introduced in 2.25.0, optional at runtime.

## [2.25.0] - 2022-02-25

- Added progress logging during long-running uploads.

## [2.24.0] - 2022-02-23

- The `Repository.is_sigstore` attribute has been deprecated.
- Fixed a crash bug when uploading files of size >1GB.

## [2.23.2] - 2022-02-22

- Improved searching capabilities for fake client.

## [2.23.1] - 2022-02-21

- Minor internal refactors for improved debuggability.

## [2.23.0] - 2022-02-07

- Added `version`, `display_order` fields to `FileUnit`.
- The `ud_file_release_mappings_2` repository note is now set on repos during publish.

## [2.22.0] - 2022-01-25

- Added `pulp_repository_pre_publish` pubtools hook.

## [2.21.0] - 2021-12-15

- Added support for orphaned units to fake client.
- The `cdn_published` field now accepts ISO8601-format timestamps.
- It is no longer possible to store duplicates in the `repository_memberships` field.

## [2.20.0] - 2021-12-10

- Added many new fields: `ModulemdUnit.dependencies`, `FileUnit.description`,
  `cdn_published` and `cdn_path` on files and RPMs, and `unit_id` on all units.
- Introduced concept of "mutable fields", which may be set during upload or using
  the new `update_content` method.

## [2.19.0] - 2021-12-06

### Fixed

- Fix `copy_content` on fake client failing to update `repository_memberships` field.

### Added

- Added `Client.search_task` for searching tasks.
- Added `requires` and `provides` attrs to `RpmUnit` class.

### Changed

- `Criteria`, `Matcher` objects now stringify more concisely.

## [2.18.0] - 2021-11-29

- Added `basic_auth_username`, `basic_auth_password` to `SyncOptions` to support
  authenticated sync tasks.
- Fake client now accurately reproduces Pulp server behavior around replacing an
  existing file/iso unit.

## [2.17.0] - 2021-10-27

- Added upload support for more content types to `YumRepository`: `upload_comps_xml`,
  `upload_erratum`, `upload_metadata`, `upload_modules`.
- Added unit models for more content types: `ErratumUnit`, `YumRepoMetadataFileUnit`.
- Added `Client.copy_content` for copying content from one repository to another.
- Changed `FileUnit` schema to accept non-integer values of `size` during load, for
  compatibility with some legacy data.
- Fixed `Task` schema too strict, formely being unable to load certain kinds of tasks
  (such as removing orphans).
- Added more verbose logging on errors during load of Pulp data.

## [2.16.0] - 2021-09-30

- Added `YumRepository.upload_rpm`.
- Internal refactoring and changes to logging of uploads.

## [2.15.0] - 2021-09-13

### Added

- Added `content_type_id` attribute to `ModuldemdDefaultsUnit` class.

## [2.14.0] - 2021-09-02

### Added

- Introduced `Criteria.with_unit_type`, to search for content of a specific type.

### Fixed

- Fixed `search_content` repeatedly querying Pulp for content type IDs.
- Fixed `upload_file` on test client not updating repository content.

### Deprecated

- Deprecated `FakeController.upload_history`. Repository content should be checked instead.

## [2.13.0] - 2021-08-24

- Searching for RPMs by sha256sum will now use the indexed `checksum` field on Pulp,
  rather than the non-indexed `checksums.sha256` field. This can significantly improve
  the performance of these searches on large systems.
- The `repository_memberships` field will now be populated in units returned from
  `search_content`.
- The `repository_memberships` field will now always be sorted to ensure stable behavior.

## [2.12.1] - 2021-08-11

- Fixed handling of `type_ids` in calls to `remove_content`. Previously, the argument
  did not result in filtering by type as expected.

## [2.12.0] - 2021-07-26

### Added

- `Client` instances can now be used in a `with` statement to manage the lifecycle
  of the underlying threads.

## [2.11.0] - 2021-07-15

### Added

- Introduced `pulp_repository_published` hook. This may be used to subscribe to all
  repository publish events triggered by this library.

### Changed

- Internal refactoring for improved debuggability.

## [2.10.0] - 2021-06-28

### Added
- Filename attribute for RpmUnit class
- nsvca property for ModulemdUnit class

## [2.9.0] - 2021-06-15
### Added
- Support for various repo notes for Repository model
- Support for various fields of ModuleMd unit
- Introduced YumRepository.get_x_repository methods that can retrieve
  related binary, debug and source repository

## [2.8.0] - 2021-03-17

### Added
- Maximum number of queued or running Pulp tasks can be customized by callers

## [2.7.0] - 2020-06-11

### Fixed
- Use repo id as registry_id when it's not set in distributor config or set to null or empty string

## [2.6.0] - 2020-05-05

### Added
- sourcerpm attribute for Rpm unit
- client.search_content method
- Introduced 'population_sources' and 'ubi_population' attributes for yum repository

### Fixed
- 'stream' and 'profiles' are now optional on modulemd_defaults units, rather
  than incorrectly mandatory (leading to schema validation errors)

## [2.5.0] - 2020-02-25

### Added
- Introduced `Repository.sync` API (and associated `SyncOptions` classes)
  for synchronizing Pulp repositories.

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

[Unreleased]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.30.0...HEAD
[2.30.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.29.0...v2.30.0
[2.29.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.28.1...v2.29.0
[2.28.1]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.28.0...v2.28.1
[2.28.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.27.0...v2.28.0
[2.27.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.26.1...v2.27.0
[2.26.1]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.26.0...v2.26.1
[2.26.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.25.1...v2.26.0
[2.25.1]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.25.0...v2.25.1
[2.25.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.24.0...v2.25.0
[2.24.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.23.2...v2.24.0
[2.23.2]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.23.1...v2.23.2
[2.23.1]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.23.0...v2.23.1
[2.23.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.22.0...v2.23.0
[2.22.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.21.0...v2.22.0
[2.21.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.20.0...v2.21.0
[2.20.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.19.0...v2.20.0
[2.19.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.18.0...v2.19.0
[2.18.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.17.0...v2.18.0
[2.17.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.16.0...v2.17.0
[2.16.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.15.0...v2.16.0
[2.15.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.14.0...v2.15.0
[2.14.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.13.0...v2.14.0
[2.13.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.12.1...v2.13.0
[2.12.1]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.12.0...v2.12.1
[2.12.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.11.0...v2.12.0
[2.11.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.10.0...v2.11.0
[2.10.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.9.0...v2.10.0
[2.9.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.8.0...v2.9.0
[2.8.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.7.0...v2.8.0
[2.7.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.6.0...v2.7.0
[2.6.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.5.0...v2.6.0
[2.5.0]: https://github.com/release-engineering/pubtools-pulplib/compare/v2.4.0...v2.5.0
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
