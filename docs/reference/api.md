# API Reference

## `wrap_all(*wrappers, config=None, enabled=True)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `*wrappers` | `Callable \| tuple[Callable, Callable]` | One or more wrappers. Each can be a single callable (used for both sync and async) or a `(sync, async)` tuple. First wrapper = innermost. |
| `config` | `DiscoveryConfig \| None` | Custom config (default: load from pyproject.toml) |
| `enabled` | `bool \| None` | `True` = always, `False` = never, `None` = read `OMNIWRAP` env var |

## `@trace(*, log, log_input, log_output, log_input_size, log_output_size, log_rss, skip_if, otel)`

Decorator for manual per-function instrumentation. Works on both sync and async functions.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `log` | `bool \| None` | `None` | Override `OMNIRAY_LOG` per-function |
| `log_input` | `bool \| None` | `None` | Override `OMNIRAY_LOG_INPUT` |
| `log_output` | `bool \| None` | `None` | Override `OMNIRAY_LOG_OUTPUT` |
| `log_input_size` | `bool \| None` | `None` | Override `OMNIRAY_LOG_INPUT_SIZE` |
| `log_output_size` | `bool \| None` | `None` | Override `OMNIRAY_LOG_OUTPUT_SIZE` |
| `log_rss` | `bool \| None` | `None` | Override `OMNIRAY_LOG_RSS` |
| `skip_if` | `Callable[..., bool] \| None` | `None` | Predicate receiving function args; skip tracing when `True` |
| `otel` | `bool \| None` | `None` | Override `OMNIRAY_OTEL` |

## `create_trace_wrapper(*, log, log_input, log_output, log_input_size, log_output_size, log_rss, skip_if, otel)`

Factory that returns `tuple[Callable, Callable]` — a `(sync_wrapper, async_wrapper)` pair for use with `wrap_all()`. Parameters are identical to `@trace`.

## `@skip_wrap`

Marker decorator that excludes a function or class from `wrap_all()` instrumentation:

```python
from omniwrap import skip_wrap

@skip_wrap
def healthcheck():
    return "ok"
```

## Safety

omniray **never wraps**:

- Dunder methods (`__init__`, `__str__`, etc.) — could break class behavior
- Properties — can't be wrapped
- Exception classes — would break exception handling
- Already-wrapped functions — prevents double-wrapping
- Imported objects — only wraps functions defined in their own module
- Functions decorated with `@trace` — prevents double instrumentation
- The omniwrap package itself — prevents infinite recursion

Exceptions are **never masked** by tracing. If your function raises, the exception propagates unchanged.

## Versioning

Both `omniwrap` and `omniray` follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and are released together under the same version number.

**Public API** (covered by semver guarantees):

- `omniwrap.wrap_all()`
- `omniwrap.skip_wrap`
- `omniray.trace()`
- `omniray.create_trace_wrapper()`
- Configuration schema in `[tool.omniwrap]`
- All environment variables listed in [Configuration](../guide/configuration.md)

**Not public API** (may change without major bump):

- Modules prefixed with `_` or nested under `tracing/`
- Internal classes (`Wrapper`, `Tracer`, `ModuleDiscovery`, etc.)
- Console output format (tree layout, colors, `[SLOW]` thresholds)
