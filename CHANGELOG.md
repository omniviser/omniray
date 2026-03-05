# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - Unreleased

### Changed
- **Renamed** `omniwrap-trace` package to `omniray`. The Python import changes from `omniwrap_trace` to `omniray`. Install with `pip install omniray`.

### Added
- `omniwrap`: Automatic function/method wrapping engine with `wrap_all()` API
- `omniwrap-trace`: OpenTelemetry tracing plugin with sync/async support
- Configuration via `[tool.omniwrap]` in `pyproject.toml`
- Environment variable control (`OMNIWRAP=true/false`)
- Console profiler with colored tree output
- Function I/O logging with Pydantic serialization
- Type-safe `@trace()` decorator preserving function signatures via `ParamSpec`

[1.0.0]: https://github.com/omniviser/omniray/releases/tag/v1.0.0
