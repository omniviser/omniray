# omniray

![omniray demo](assets/demo.gif)

## Why omniray?

- **Zero-touch instrumentation** — One call wraps every function and method in your codebase. No `@decorator` on each function, no manual setup per module.
- **Live call tree** — See the full call hierarchy in your terminal as it happens, with color-coded timing (green/yellow/red) and `[SLOW]` tags on bottlenecks. Unlike cProfile or py-spy, there's no post-mortem step.
- **OpenTelemetry bridge** — Flip one flag to export spans to Jaeger, Datadog, or any OTel-compatible backend. Cherry-pick which functions get spans.
- **Production-safe** — Never masks exceptions, never wraps dunders or properties, skips already-wrapped functions. Designed to be safe even if accidentally left on.

[Quick Setup](getting-started/){ .md-button .md-button--primary }
