# omniray

[![Tests](https://github.com/omniviser/omniray/actions/workflows/test.yml/badge.svg)](https://github.com/omniviser/omniray/actions/workflows/test.yml)
[![Lint](https://github.com/omniviser/omniray/actions/workflows/lint.yml/badge.svg)](https://github.com/omniviser/omniray/actions/workflows/lint.yml)
[![codecov](https://codecov.io/gh/omniviser/omniray/graph/badge.svg)](https://codecov.io/gh/omniviser/omniray)
[![PyPI](https://img.shields.io/pypi/v/omniray)](https://pypi.org/project/omniray/)
[![Python](https://img.shields.io/pypi/pyversions/omniray)](https://pypi.org/project/omniray/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Live tracing for Python** — see every function call as a color-coded tree in your terminal, with optional OpenTelemetry spans. No manual decorators needed.

omniray is a monorepo with two packages: **[omniray](#packages)** (live tracing — console tree + OpenTelemetry) powered by **[omniwrap](#packages)** (automatic wrapping engine). One call instruments your entire codebase. Built and battle-tested at [OMNIVISER](https://omniviser.ai).

### See it in action

Two lines of code — your entire codebase gets tracing with live console output:

```python
from omniwrap import wrap_all
from omniray import create_trace_wrapper

wrap_all(create_trace_wrapper())  # like putting @trace on every function and method in your codebase
```

```
14:23  INFO: ┌─ AuthMiddleware.__call__
14:23  INFO: │  ├─ ┌─ TokenService.authenticate
14:23  INFO: │  │  ├─ ┌─ TokenService._extract_bearer_token
14:23  INFO: │  │  │  ├─ ┌─ SessionStore.get_token
14:23  INFO: │  │  │  │  └─ (850.75ms) SessionStore.get_token [SLOW]
14:23  INFO: │  │  │  └─ (851.25ms) TokenService._extract_bearer_token [SLOW]
14:23  INFO: │  │  ├─ ┌─ JWTValidator.decode_and_verify
14:23  INFO: │  │  │  └─ (335.23ms) JWTValidator.decode_and_verify [SLOW]
14:23  INFO: │  │  ├─ ┌─ PermissionService.check_access
14:23  INFO: │  │  │  └─ (12.43ms) PermissionService.check_access
14:23  INFO: │  │  └─ (1200.07ms) TokenService.authenticate [SLOW]
14:23  INFO: │  ├─ ┌─ OrderView.get
14:23  INFO: │  │  ├─ ┌─ OrderView.check_permissions
14:23  INFO: │  │  │  └─ (0.01ms) OrderView.check_permissions
14:23  INFO: │  │  ├─ ┌─ OrderView.get_context
14:23  INFO: │  │  │  └─ (0.05ms) OrderView.get_context
14:23  INFO: │  │  └─ (32.69ms) OrderView.get
14:23  INFO: │  └─ (1234.08ms) AuthMiddleware.dispatch [SLOW]
14:23  INFO: └─ (1247.51ms) AuthMiddleware.__call__ [SLOW]

INFO:     192.168.1.42:51203 - "GET /api/orders/ HTTP/1.1" 200 OK
```

Every function call becomes a span — timing is color-coded in the terminal (dim < 1ms, green < 10ms, yellow < 100ms, red above), `[SLOW]` tags highlight bottlenecks, and the tree shows the full call hierarchy. Regular application logs flow naturally between traces. With `omniray[otel]`, all spans are simultaneously exported to your OpenTelemetry backend.

## Packages

| Package | What it does | Install |
|---------|-------------|---------|
| [omniray](packages/omniray/) | Live tracing — console tree + OpenTelemetry | `pip install omniray` |
| [omniwrap](packages/omniwrap/) | Wrapping engine that omniray is built on | `pip install omniwrap` |

`omniray` depends on `omniwrap`, so installing `omniray` installs both. For OpenTelemetry support:

```bash
pip install omniray[otel]   # adds opentelemetry-api + opentelemetry-sdk
```

## Installation

```bash
# Custom wrappers only (no tracing)
pip install omniwrap

# Console tracing
pip install omniray

# Console tracing + OpenTelemetry spans
pip install omniray[otel]
```

Requires Python >= 3.12.

## Quick Start

### With omniray (recommended)

```python
from omniwrap import wrap_all
from omniray import create_trace_wrapper

wrap_all(create_trace_wrapper())
```

Then enable console output:

```bash
OMNIRAY_LOG=true python app.py
```

### Custom wrapper (omniwrap only)

```python
from omniwrap import wrap_all

def log_calls(wrapped, instance, args, kwargs):
    print(f"Calling {wrapped.__qualname__}")
    return wrapped(*args, **kwargs)

wrap_all(log_calls)  # Done. Every function is now wrapped.
```

With separate sync/async wrappers:

```python
wrap_all((sync_wrapper, async_wrapper))
```

Multiple wrappers (first = innermost, closest to the original function):

```python
wrap_all(log_calls, (sync_trace, async_trace))
```

## `@trace` Decorator

Use `@trace` for manual per-function instrumentation. For automatic instrumentation of your entire codebase, use `create_trace_wrapper()` with `wrap_all()` instead.

```python
from omniray import trace

@trace(
    log=None,         # Override OMNIRAY_LOG per-function
    log_input=None,   # Override OMNIRAY_LOG_INPUT per-function
    log_output=None,  # Override OMNIRAY_LOG_OUTPUT per-function
    skip_if=None,     # Predicate: skip tracing when True
    otel=None,        # Override OMNIRAY_OTEL per-function
)
def my_function(): ...
```

### I/O logging

```python
@trace(log_input=True, log_output=True)
def send_message(conversation_id: str, content: str, mode: str): ...
```

```
14:23  INFO: ┌─ ChatService.send_message
14:23  INFO: IN: {
14:23  INFO:   "conversation_id": "8467faba-378e-43e1-a757-970df1e05f1f",
14:23  INFO:   "content": "who is the president of France?",
14:23  INFO:   "mode": "web_search"
14:23  INFO: }
14:23  INFO: │  ├─ ┌─ SearchProvider.web_search
14:23  INFO: │  │  └─ (2737.41ms) SearchProvider.web_search [SLOW]
14:23  INFO: │  ├─ ┌─ SearchResult.extract_sources
14:23  INFO: │  │  └─ (0.32ms) SearchResult.extract_sources
14:23  INFO: │  ├─ ┌─ Message.to_schema
14:23  INFO: │  │  ├─ ┌─ Source.to_schema
14:23  INFO: │  │  │  └─ (0.08ms) Source.to_schema
14:23  INFO: │  │  ├─ ┌─ Source.to_schema
14:23  INFO: │  │  │  └─ (0.01ms) Source.to_schema
14:23  INFO: │  │  └─ (133.96ms) Message.to_schema
14:23  INFO: │  └─ (4095.51ms) ChatService.send_message [SLOW]
14:23  INFO: OUT: {
14:23  INFO:   "id": "2fda24e1-fb2f-428d-a9c5-16361fd1f049",
14:23  INFO:   "content": "The current president of France is Emmanuel Macron.",
14:23  INFO:   "sources": [{"title": "...", "url": "..."}, ...],
14:23  INFO:   "mode": "web_search"
14:23  INFO: }
14:23  INFO: └─ (4460.29ms) ChatService.send_message [SLOW]
```

> **Warning:** `log_input` and `log_output` serialize function arguments and return values to the console. Make sure your secrets are properly protected — e.g. stored in Pydantic's `SecretStr`, which redacts values in `repr()` and JSON output. Plain `str` passwords or API keys **will** appear in your logs.

You can also enable I/O logging globally via environment variables (not recommended — prefer `@trace` on specific functions):

```bash
OMNIRAY_LOG=true OMNIRAY_LOG_INPUT=true OMNIRAY_LOG_OUTPUT=true python app.py
```

### Conditional skip

```python
@trace(skip_if=lambda path, **kw: path == "/healthz")
def handle_request(path: str, method: str): ...
```

When `skip_if` returns `True`, tracing is bypassed entirely and the function is called directly.

### Selective OpenTelemetry

You don't have to choose between "OTel everywhere" and "OTel nowhere". Use `@trace(otel=True)` to create spans only for the functions that matter — critical business logic, slow paths, external calls — while keeping the rest of your codebase trace-free:

```python
@trace(otel=True)
def process_payment(order_id: str) -> bool: ...

@trace(otel=True, log_input=True)
async def call_external_api(endpoint: str, payload: dict) -> Response: ...
```

This works independently of `OMNIRAY_OTEL`. Even with `OMNIRAY_OTEL` unset globally, functions with `otel=True` will emit spans. Conversely, `OMNIRAY_OTEL=false` acts as a kill switch and disables spans everywhere — including per-function overrides.

### Double-wrapping prevention

Functions decorated with `@trace` are automatically excluded from `wrap_all()` instrumentation. You can safely use both `@trace` (for per-function config) and `wrap_all(create_trace_wrapper())` (for everything else) in the same codebase.

## Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OMNIWRAP` | bool | `false` | Enable/disable wrapping when `enabled=None` is passed to `wrap_all()` |

The remaining omniray flags use a **tri-state** system:

- **`true`** — enabled
- **`false`** — **kill switch** (overrides all decorator parameters, cannot be turned back on per-function)
- **unset** — local decides (decorator parameters or defaults apply)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OMNIRAY_LOG` | bool | unset | Console tree output |
| `OMNIRAY_LOG_INPUT` | bool | unset | Log function arguments (requires `OMNIRAY_LOG`) |
| `OMNIRAY_LOG_OUTPUT` | bool | unset | Log function return values (requires `OMNIRAY_LOG`) |
| `OMNIRAY_LOG_COLOR` | bool | `true` | ANSI colors in console output |
| `OMNIRAY_LOG_STYLE` | str | `auto` | Box-drawing style: `unicode`, `ascii`, or `auto` |
| `OMNIRAY_OTEL` | bool | unset | OpenTelemetry span creation |

### Flag resolution

The global flag (env var) and local flag (`@trace` parameter) are merged with kill-switch semantics:

```
OMNIRAY_LOG=false + @trace(log=True)  →  False   (kill switch wins)
OMNIRAY_LOG=true  + @trace(log=None)  →  True    (global enables)
OMNIRAY_LOG unset + @trace(log=True)  →  True    (local decides)
OMNIRAY_LOG unset + @trace(log=None)  →  False   (both unset → off)
```

## Configuration

Configure module discovery via `[tool.omniwrap]` in your `pyproject.toml`:

```toml
[tool.omniwrap]
paths = ["src", "app"]                    # Directories to scan (default: current dir)
exclude = ["migrations", "scripts"]       # Added to built-in exclusions
skip_wrap = ["to_pydantic", "serialize"]  # Function/method names to never wrap
```

Built-in exclusions (always applied): `.venv`, `__pycache__`, `.git`, `.hg`, `.pytest_cache`, `__init__.py`, `__main__.py`, `asgi.py`, `wsgi.py`.

### Enabling / Disabling

The `enabled` parameter on `wrap_all` gives you full control over when wrapping is active:

```python
wrap_all(wrappers, enabled=True)   # Always enabled (default)
wrap_all(wrappers, enabled=False)  # Always disabled (no-op)
wrap_all(wrappers, enabled=None)   # Read from OMNIWRAP env var
```

Wire to your own flag or environment:

```python
wrap_all(wrappers, enabled=settings.TRACING_ENABLED)
```

```bash
OMNIWRAP=true python app.py   # Wrapping enabled
OMNIWRAP=false python app.py  # Wrapping disabled
```

## How It Works

```
wrap_all(*wrappers)
  │
  ├─ Load config from pyproject.toml
  ├─ Discover all .py files in configured paths
  ├─ Import each module
  └─ For each function/method:
      ├─ Skip if: dunder, property, exception class, @skip_wrap, already wrapped
      ├─ Detect sync vs async
      └─ Apply wrapper via wrapt (safe monkey-patching)
```

## Writing Custom Wrappers

A wrapper is any callable with the [wrapt signature](https://wrapt.readthedocs.io/en/latest/wrappers.html):

```python
def my_wrapper(wrapped, instance, args, kwargs):
    # wrapped   - the original function
    # instance  - None for functions, self/cls for methods
    # args      - positional arguments
    # kwargs    - keyword arguments

    # ... do something before ...
    result = wrapped(*args, **kwargs)
    # ... do something after ...
    return result
```

For async functions, provide a separate async wrapper:

```python
async def my_async_wrapper(wrapped, instance, args, kwargs):
    result = await wrapped(*args, **kwargs)
    return result

wrap_all((my_wrapper, my_async_wrapper))
```

## API Reference

### `wrap_all(*wrappers, config=None, enabled=True)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `*wrappers` | `Callable \| tuple[Callable, Callable]` | One or more wrappers. Each can be a single callable (used for both sync and async) or a `(sync, async)` tuple. First wrapper = innermost. |
| `config` | `DiscoveryConfig \| None` | Custom config (default: load from pyproject.toml) |
| `enabled` | `bool \| None` | `True` = always, `False` = never, `None` = read `OMNIWRAP` env var |

### `@trace(*, log, log_input, log_output, skip_if, otel)`

Decorator for manual per-function instrumentation. Works on both sync and async functions.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `log` | `bool \| None` | `None` | Override `OMNIRAY_LOG` per-function |
| `log_input` | `bool \| None` | `None` | Override `OMNIRAY_LOG_INPUT` |
| `log_output` | `bool \| None` | `None` | Override `OMNIRAY_LOG_OUTPUT` |
| `skip_if` | `Callable[..., bool] \| None` | `None` | Predicate receiving function args; skip tracing when `True` |
| `otel` | `bool \| None` | `None` | Override `OMNIRAY_OTEL` |

### `create_trace_wrapper(*, log, log_input, log_output, skip_if, otel)`

Factory that returns `tuple[Callable, Callable]` — a `(sync_wrapper, async_wrapper)` pair for use with `wrap_all()`. Parameters are identical to `@trace`.

### `@skip_wrap`

Marker decorator that excludes a function or class from `wrap_all()` instrumentation:

```python
from omniwrap import skip_wrap

@skip_wrap
def healthcheck():
    return "ok"
```

## Safety

omniwrap is designed to be **safe to run in production** when needed — it won't break your application, mask exceptions, or cause side effects. However, console tracing (`OMNIRAY_LOG`) is intended for debugging sessions, not continuous production use. It **never wraps**:

- Dunder methods (`__init__`, `__str__`, etc.) — could break class behavior
- Properties — can't be wrapped
- Exception classes — would break exception handling
- Already-wrapped functions — prevents double-wrapping
- Imported objects — only wraps functions defined in their own module
- Functions decorated with `@trace` — prevents double instrumentation
- The omniwrap package itself — prevents infinite recursion

Exceptions are **never masked** by tracing. If your function raises, the exception propagates unchanged.

## Performance

### omniwrap

omniwrap uses [wrapt](https://github.com/GrahamDumpleton/wrapt) for monkey-patching, which adds a small per-call overhead. Measured on Apple M4, Python 3.13:

| Scenario | Per call | Overhead |
|----------|----------|----------|
| Direct call (baseline) | ~15 ns | — |
| Wrapped (no-op wrapper) | ~250 ns | **~235 ns** |
| Wrapped (with timing) | ~325 ns | ~310 ns |

**~200-300 ns per wrapped call.** A typical web request with 200 wrapped calls adds ~50 μs — less than 0.01% of a 500ms response. A single database query (~5 ms) costs as much as ~20,000 wrapped calls.

### omniray

omniray adds per-call overhead on top of omniwrap. Measured on Apple M4, Python 3.14:

| Scenario | Per call | Overhead |
|----------|----------|----------|
| Tracing wired, all flags off | ~1.0 μs | **~1 μs** |
| `OMNIRAY_LOG=true` (console output) | ~17 μs | **~17 μs** |
| `OMNIRAY_LOG=true` + `LOG_INPUT` + `LOG_OUTPUT` | ~45 μs | **~45 μs** |

The overhead depends on which features are active:

- **Flags off** (~1 μs) — flag resolution, span name generation, two `time.time()` calls, and ContextVar bookkeeping. This is the minimum cost when omniray is wired up but not logging.
- **Console logging** (~17 μs) — the dominant cost is Python's `logging` module: 3× `logger.info()` per call, each acquiring a thread lock, formatting the tree structure (indentation, box-drawing characters, color codes), and writing to stderr. Unlike post-mortem profilers (cProfile, py-spy) that defer display to the end, omniray formats output **live per call**.
- **I/O logging** (~45 μs) — serializes arguments and return values via `pydantic_core.to_jsonable_python()` + `json.dumps()`. Designed for selective use on specific functions via `@trace(log_input=True)`.
- **OpenTelemetry spans** (`OMNIRAY_OTEL`) — creates and closes an OTel span, sets attributes. Cost depends on your exporter and span processor.

A typical debugging session tracing **50** function calls per request adds **~0.8 ms** with console
logging.

Run benchmarks yourself:

```bash
python benchmarks/bench_overhead.py           # omniwrap wrapping overhead
python benchmarks/bench_tracer_overhead.py    # omniray tracing overhead
```

## Examples

See the [examples/](examples/) directory:

- [basic_logging.py](examples/basic_logging.py) — Automatic function call logging
- [basic_timing.py](examples/basic_timing.py) — Execution time measurement
- [otel_tracing.py](examples/otel_tracing.py) — OpenTelemetry tracing with omniray

## Versioning

Both `omniwrap` and `omniray` follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and are released together under the same version number.

**Public API** (covered by semver guarantees):
- `omniwrap.wrap_all()`
- `omniwrap.skip_wrap`
- `omniray.trace()`
- `omniray.create_trace_wrapper()`
- Configuration schema in `[tool.omniwrap]`
- All environment variables listed in this README

**Not public API** (may change without major bump):
- Modules prefixed with `_` or nested under `tracing/`
- Internal classes (`Wrapper`, `Tracer`, `ModuleDiscovery`, etc.)
- Console output format (tree layout, colors, `[SLOW]` thresholds)

### What counts as a breaking change

| Change | Breaking? |
|--------|-----------|
| Removing or renaming a public function | Yes |
| Changing default behavior of `wrap_all()` | Yes |
| Adding a new optional parameter | No |
| Adding new environment variables | No |
| Changing console output format | No |
| Changing internal module structure | No |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
