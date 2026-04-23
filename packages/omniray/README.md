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
| `OMNIRAY_LOG_RSS` | `false` | Append process RSS (current MB, delta before→after, peak since process start) to the timing line. Current RSS uses `psutil`; peak uses `resource.getrusage` (Unix). ~5–20µs per call. |
| `OMNIRAY_LOG_COLOR` | `true` | Enable ANSI colors in console output |
| `OMNIRAY_LOG_STYLE` | `auto` | Box-drawing style: `unicode`, `ascii`, or `auto` (detect from terminal) |

## Configuration via `pyproject.toml`

Color thresholds for the per-segment coloring of the timing line live under
`[tool.omniray.thresholds]` in the host project's `pyproject.toml`. Each list
defines the `DIM → GREEN → YELLOW → RED` boundaries for its value class.

```toml
[tool.omniray.thresholds]
size = [0.1, 1, 10]              # MB: in/out payload (DIM < 0.1, GREEN < 1, YELLOW < 10, RED ≥ 10)
rss = [100, 500, 1000]           # MB: rss current / peak
rss_delta = [1, 10, 100]         # MB: RSS delta (negative / near-zero → DIM)
duration_ms = [1, 10, 100]       # ms: span duration color boundaries
size_big_tag_mb = 10             # MB: in/out size at/above which the `[BIG]` tag is appended
duration_slow_tag_ms = 200       # ms: duration at/above which the `[SLOW]` tag is appended
```

All keys are optional — omitted ones fall back to defaults shown above. The
file is resolved by walking up from the current working directory until the
first `pyproject.toml` is found; missing/malformed files cause silent fallback
to defaults. Thresholds are loaded once at import time; restart the process to
pick up changes.

## License

Apache 2.0
