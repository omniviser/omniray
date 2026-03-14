# Getting Started

## Requirements

- Python >= 3.12

## Install

=== "Console tracing"

    ```bash
    pip install omniray
    ```

=== "Console tracing + OpenTelemetry"

    ```bash
    pip install omniray[otel]
    ```

=== "Wrapping engine only"

    ```bash
    pip install omniwrap
    ```

omniray is built on [omniwrap](https://github.com/omniviser/omniray/tree/main/packages/omniwrap) — installing omniray installs both.

| Package | What it does |
|---------|-------------|
| [omniray](https://pypi.org/project/omniray/) | Live tracing — console tree + OpenTelemetry |
| [omniwrap](https://pypi.org/project/omniwrap/) | Wrapping engine that omniray is built on |

## Quick Start

One call to instrument your entire codebase:

```python
from omniwrap import wrap_all
from omniray import create_trace_wrapper

wrap_all(create_trace_wrapper())
```

Then enable console output:

```bash
OMNIRAY_LOG=true python app.py
```

Every function call becomes a span — timing is color-coded in the terminal (dim < 1ms, green < 10ms, yellow < 100ms, red above), `[SLOW]` tags highlight bottlenecks, and the tree shows the full call hierarchy.

## With omniwrap only (custom wrappers)

```python
from omniwrap import wrap_all

def log_calls(wrapped, instance, args, kwargs):
    print(f"Calling {wrapped.__qualname__}")
    return wrapped(*args, **kwargs)

wrap_all(log_calls)  # Done. Every function is now wrapped.
```

See [Custom Wrappers](../guide/custom-wrappers.md) for more.
