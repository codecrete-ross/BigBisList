# Changelog

## 0.12.1 - 2026-08-29

### Added

- GitHub Actions now runs the authoritative full release gate for pull requests
  and numeric release tags.

### Changed

- Each release now publishes a release-specific changelog containing only the
  changes shipped since the prior tag; historical notes remain in Git history.
- Release documentation now makes CurseForge's automatic tag, package metadata,
  and changelog ingestion explicit, with no manual author-UI step.

### Fixed

- Release validation now rejects cumulative, missing, empty, mismatched, or
  unchanged changelogs before a new tag is published.
- Windows release-check coverage now handles Lua runtime and compiler tools
  installed in different directories.
