---
layout: page
title: "Changelog"
category: dev
date: 2013-06-12 08:54:47
---

### [2.0.16](https://github.com/cbmi/serrano/compare/2.0.15...HEAD) (in development)

- Update minimum Avocado version to 2.0.22
- Update minimum django-preserialize version to 1.0.4
- Add support for Django 1.5
- Moved references of settings inside function calls
    - This is primarily for testing purposes
- Minor breaking changes
    - The `data` prefix from URL reverse names have been removed
    - Internal resource classes and modules have been renamed

### [2.0.15](https://github.com/cbmi/serrano/compare/2.0.14...2.0.15)

- Update minimum Avocado version to 2.0.19
- Add quotes around Content-Disposition filename
    - See http://kb.mozillazine.org/Filenames_with_spaces_are_truncated_upon_download

### [2.0.14](https://github.com/cbmi/serrano/compare/2.0.13...2.0.14)

- Change URLs to be absolute URIs rather than relative to host
    - For cross-origin sharing, absolute URIs are needed

### [2.0.13](https://github.com/cbmi/serrano/compare/2.0.12...2.0.13)

- Fix incorrect base class name for Export- and Preview- resources

### [2.0.12](https://github.com/cbmi/serrano/compare/2.0.11...2.0.12)

- Add support for user-derived API tokens
    - Upon successful authentication against the root endpoint, a token will
    be returned that can be used for subsequent requests.
- Add support for Cross-Origin Resource Sharing (CORS)
    - This includes two new settings `SERRANO_CORS_ENABLED` and
    `SERRANO_CORS_ORIGIN`.
- Add API version to root endpoint for reference. This is derived from the
major and minor version of Serrano, e.g. 2.0.12 -> 20

### [2.0.11](https://github.com/cbmi/serrano/compare/2.0.10...2.0.11)

- Abstract out logic for resolving `DataView` and `DataContext` objects
- Update tests to require Avocado 2.0.13+

### [2.0.10](https://github.com/cbmi/serrano/compare/2.0.9...2.0.10)

- Fix missing increment of `exporter.row_length` for dealing with reundant
rows in Avocado 2.0.9+

### [2.0.9](https://github.com/cbmi/serrano/compare/2.0.8...2.0.9)

- Add missing `post` method on data preview resource (from 2.0.7)

### [2.0.8](https://github.com/cbmi/serrano/compare/2.0.7...2.0.8)

- Remove map of `operator_choices` to `operators`
    - Change made in Avocado 2.0.10

### [2.0.7](https://github.com/cbmi/serrano/compare/2.0.6...2.0.7)

- Add support for defining the `context` and `view` objects via a POST request
    - This enables performing one-off (non-persisted) queries
- Abstract out the browser-based *data preview* resource from the format export mechanism
- Change export endpoint `/api/data/export/` to return an object of possible export formats
    - Each export target has it's own endpoint, e.g. `/api/data/export/sas/` for SAS export

### [2.0.6](https://github.com/cbmi/serrano/compare/2.0.5...2.0.6)

- Update django-preserialize 1.0 to make use of the `allow_missing` option
    - This prevents missing keys or attributes from throwing an exception
- Add `DataConcept.sortable` field from Avocado 2.0.8+

### [2.0.5](https://github.com/cbmi/serrano/compare/2.0.4...2.0.5)

- #21 - Fix the `ExporterResource` to use the `DjangoJSONEncoder` to correctly handle datetimes and `Decimal`s

### [2.0.4](https://github.com/cbmi/serrano/compare/2.0.3...2.0.4)

- Change behavior of `DataContextResource` to recalculate count only [if at least one condition is present](https://github.com/cbmi/serrano/commit/a774621a2788f8b2736e6a5675d5ba6bdeb4163e)
- Integrate history API settings from Avocado 2.0.7+
    - Instances are no longer auto-archived, but [are conditional](https://github.com/cbmi/serrano/commit/73d5ba5a44a5f06ea7342a5f627dc71b621aa09b) based the `HISTORY_ENABLED` setting

### [2.0.3](https://github.com/cbmi/serrano/compare/2.0.2...2.0.3)

- Fix incorrect use of `sys.version_info`

### [2.0.2](https://github.com/cbmi/serrano/compare/2.0.1...2.0.2)

- Add Python 2.6 support

### [2.0.1](https://github.com/cbmi/serrano/compare/2.0.0...2.0.1)

- Fix erroneous reset of kwargs in `DataContextResource` and `DataViewResource`

### 2.0.0 - Initial release
