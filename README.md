<div align="center">

<img src="docs/assets/omniray_logo.png" alt="omniray logo" width="400"><br><br>

[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=omniviser_omniray&metric=coverage)](https://sonarcloud.io/summary/new_code?id=omniviser_omniray)
[![Tests](https://github.com/omniviser/omniray/actions/workflows/test.yml/badge.svg)](https://github.com/omniviser/omniray/actions/workflows/test.yml)
[![Lint](https://github.com/omniviser/omniray/actions/workflows/lint.yml/badge.svg)](https://github.com/omniviser/omniray/actions/workflows/lint.yml)
[![CodeQL](https://github.com/omniviser/omniray/actions/workflows/codeql.yml/badge.svg)](https://github.com/omniviser/omniray/actions/workflows/codeql.yml)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=omniviser_omniray&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=omniviser_omniray)
<br>
[![PyPI](https://img.shields.io/pypi/v/omniray)](https://pypi.org/project/omniray/)
[![Python](https://img.shields.io/pypi/pyversions/omniray)](https://pypi.org/project/omniray/)
[![Docs](https://img.shields.io/badge/docs-blue)](https://omniviser.github.io/omniray/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**One call, and you see everything that's happening in your code.**

Meet omniray — OMNIVISER's X-RAY

Built and battle-tested at [OMNIVISER](https://omniviser.ai).

</div>

---

## How it works

> Demo app built to show omniray(v1.0) in action — every function call traced live with timing and I/O.

<p align="center">
  <img src="docs/assets/demo.gif" alt="omniray demo" width="700">
</p>

- Live `function`, `error`, `I/O` and `performance` tracing in clear logs.
- Full context for you and your AI.
- No decorators, no config files — just one call.

## Quick Setup

Install:

```bash
pip install omniray              # console tracing
pip install omniray[otel]        # + OpenTelemetry spans
pip install omniwrap             # wrapping engine only (custom wrappers)
```

Requires Python >= 3.12. omniray is built on [omniwrap](packages/omniwrap/) — installing omniray installs both.

Add to your code:

```python
from omniwrap import wrap_all
from omniray import create_trace_wrapper

wrap_all(create_trace_wrapper())
```

Run your app:

```bash
OMNIRAY_LOG=true python app.py
```

Output:

```
13:44  INFO: ┌─ BigRedButton.press
13:44  INFO: ├─ ┌─ BigRedButton.pre_launch_check
13:44  INFO: │  ├─ ┌─ MissileLauncher.authenticate
13:44  INFO: │  │  └─ (52.80ms) MissileLauncher.authenticate
13:44  INFO: │  └─ (53.34ms) BigRedButton.pre_launch_check
13:44  INFO: ├─ ┌─ BigRedButton.launch_sequence
13:44  INFO: │  ├─ ┌─ MissileLauncher.arm_warhead
13:44  INFO: │  │  └─ (124.97ms) MissileLauncher.arm_warhead
13:44  INFO: │  ├─ ┌─ MissileLauncher.select_target
13:44  INFO: │  │  IN: {
13:44  INFO: │  │    "coordinates": "51.5074° N, 0.1278° W"
13:44  INFO: │  │  }
13:44  INFO: │  │  └─ (34.74ms) MissileLauncher.select_target
13:44  INFO: │  ├─ ┌─ MissileLauncher.fire
13:44  INFO: │  │  └─ (202.05ms) MissileLauncher.fire [SLOW]
13:44  INFO: │  │  OUT: {
13:44  INFO: │  │    "status": "BOOM!",
13:44  INFO: │  │    "impact": true,
13:44  INFO: │  │    "debris_radius_km": 4.2
13:44  INFO: │  │  }
13:44  INFO: │  └─ (363.92ms) BigRedButton.launch_sequence [SLOW]
13:44  INFO: └─ (418.23ms) BigRedButton.press [SLOW]
```

## Why omniray?

- **Zero-touch instrumentation** — One call wraps every function and method in your codebase. No `@decorator` on each function, no manual setup per module.
- **Live call tree** — See the full call hierarchy in your terminal as it happens, with color-coded timing (green/yellow/red) and `[SLOW]` tags on bottlenecks. Unlike cProfile or py-spy, there's no post-mortem step.
- **OpenTelemetry bridge** — Flip one flag to export spans to Jaeger, Datadog, or any OTel-compatible backend. Cherry-pick which functions get spans.
- **Production-safe** — Never masks exceptions, never wraps dunders or properties, skips already-wrapped functions. Designed to be safe even if accidentally left on.

## Features

- **[`@trace` decorator](https://omniviser.github.io/omniray/guide/trace-decorator/)** — Per-function control over logging, I/O capture, and OTel spans
- **[I/O logging](https://omniviser.github.io/omniray/guide/trace-decorator/#io-logging)** — Log function arguments and return values for selected functions
- **[Conditional skip](https://omniviser.github.io/omniray/guide/trace-decorator/#conditional-skip)** — Skip tracing for health checks or noisy functions via `skip_if`
- **[Selective OpenTelemetry](https://omniviser.github.io/omniray/guide/trace-decorator/#selective-opentelemetry)** — Enable OTel spans on specific functions without global overhead
- **[Custom wrappers](https://omniviser.github.io/omniray/guide/custom-wrappers/)** — Build your own wrappers with the omniwrap engine
- **[Configuration](https://omniviser.github.io/omniray/guide/configuration/)** — Control paths, exclusions, and behavior via `pyproject.toml` and env vars

## Performance

**~250 ns** per wrapped call (omniwrap). **~17 us** per traced call with console output (omniray). A typical request tracing 50 functions adds under 1 ms.

## Safety

omniray **never wraps**: dunder methods, properties, exception classes, already-wrapped functions, imported objects, functions decorated with `@trace`, or its own package. Exceptions are **never masked** — if your function raises, the exception propagates unchanged.

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

## Documentation

**[Read the full docs](https://omniviser.github.io/omniray/)** — configuration, API reference, performance benchmarks, examples, and more.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
