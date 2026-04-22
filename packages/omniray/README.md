# omniray

A live tracing tool for Python -- console profiling with optional OpenTelemetry tracing for [omniwrap](https://github.com/omniviser/omniray).

See the [main README](../../README.md) for full documentation.

## Installation

```bash
pip install omniray
```

## Quick Start

```python
from omniwrap import wrap_all
from omniray import create_trace_wrapper, trace

# Auto-instrument with console profiling (OTel spans off by default)
wrap_all(create_trace_wrapper())

# Selectively enable OTel on high-value functions
@trace(otel=True)
def process_payment(order_id: str) -> bool: ...

@trace(otel=True)
async def execute_sql(query: str) -> list[dict]: ...

# Regular functions get profiling only — no OTel cost
@trace()
def validate_input(data: dict) -> bool: ...
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OMNIRAY_OTEL` | `false` | Generate OpenTelemetry spans globally (use `@trace(otel=True)` for selective opt-in) |
| `OMNIRAY_LOG` | `false` | Enable colored console tree output |
| `OMNIRAY_LOG_INPUT` | `false` | Log function arguments |
| `OMNIRAY_LOG_OUTPUT` | `false` | Log function return values |
| `OMNIRAY_LOG_INPUT_SIZE` | `false` | Append deep input size (MB) to the timing line. Uses `pympler.asizeof` — opt-in, can be slow on very large object graphs. |
| `OMNIRAY_LOG_OUTPUT_SIZE` | `false` | Append deep return-value size (MB) to the timing line. Uses `pympler.asizeof` — opt-in, can be slow on very large object graphs. |
| `OMNIRAY_SIZE_WARNING_MB` | `10` | MB threshold above which a `[BIG]` warning tag appears next to the span name when input/output size measurement is enabled. |
| `OMNIRAY_LOG_COLOR` | `true` | Enable ANSI colors in console output |
| `OMNIRAY_LOG_STYLE` | `auto` | Box-drawing style: `unicode`, `ascii`, or `auto` (detect from terminal) |

## License

Apache 2.0
