# omniray

**Find your bottleneck in one call.**

Automatic tracing for Python. See every function call as a live, color-coded tree in your terminal. No decorators, no config files — just one call.

<!-- TODO: Replace with asciinema/VHS recording -->
<!-- ![omniray demo](assets/demo.gif) -->

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
```

## Why omniray?

- **Zero-touch instrumentation** — One call wraps every function and method in your codebase. No `@decorator` on each function, no manual setup per module.
- **Live call tree** — See the full call hierarchy in your terminal as it happens, with color-coded timing (green/yellow/red) and `[SLOW]` tags on bottlenecks. Unlike cProfile or py-spy, there's no post-mortem step.
- **OpenTelemetry bridge** — Flip one flag to export spans to Jaeger, Datadog, or any OTel-compatible backend. Cherry-pick which functions get spans.
- **Production-safe** — Never masks exceptions, never wraps dunders or properties, skips already-wrapped functions. Designed to be safe even if accidentally left on.

## Quick Start

```python
from omniwrap import wrap_all
from omniray import create_trace_wrapper

wrap_all(create_trace_wrapper())
```

```bash
OMNIRAY_LOG=true python app.py
```

That's it. Every function call in your codebase now appears as a timed, nested tree in your terminal.

[Get started](getting-started/installation.md){ .md-button .md-button--primary }
