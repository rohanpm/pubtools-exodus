# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- n/a

## [1.1.0] - 2022-06-13

### Changed

- Automatically poll commit for completion once published
- Improve logging for commit publishes
- Misc. clean-up, update pre-commit hooks

## [1.0.2] - 2022-04-27

### Fixed

- pubtools-exodus-push: Fix crash when EXODUS_ENABLED is not set or false

## [1.0.1] - 2022-04-05

### Fixed

- Check EXODUS_ENABLED before populating vars from env 

## [1.0.0] - 2022-03-23

### Changed

- pubtools-exodus-push: Load content using the pushsource library

## [0.1.0] - 2022-02-24

- Initial release
- Introduce pubtools-exodus-push entry point task
- Introduce exodus-pulp hook implementers
- Introduce project structure, config, CI

[Unreleased]: https://github.com/release-enineering/pubtools-exodus/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/release-engineering/pubtools-exodus/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/release-engineering/pubtools-exodus/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/release-engineering/pubtools-exodus/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/release-engineering/pubtools-exodus/compare/v0.1.0...v1.0.0
