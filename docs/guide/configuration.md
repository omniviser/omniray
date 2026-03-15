# Configuration

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

## Flag Resolution

The global flag (env var) and local flag (`@trace` parameter) are merged with kill-switch semantics:

```
OMNIRAY_LOG=false + @trace(log=True)  →  False   (kill switch wins)
OMNIRAY_LOG=true  + @trace(log=None)  →  True    (global enables)
OMNIRAY_LOG unset + @trace(log=True)  →  True    (local decides)
OMNIRAY_LOG unset + @trace(log=None)  →  False   (both unset → off)
```

## Module Discovery

Configure module discovery via `[tool.omniwrap]` in your `pyproject.toml`:

```toml
[tool.omniwrap]
paths = ["src", "app"]                    # Directories to scan (default: current dir)
exclude = ["migrations", "scripts"]       # Added to built-in exclusions
skip_wrap = ["to_pydantic", "serialize"]  # Function/method names to never wrap
```

!!! note "Built-in exclusions"

    Always applied: `.venv`, `__pycache__`, `.git`, `.hg`, `.pytest_cache`, `__init__.py`, `__main__.py`, `asgi.py`, `wsgi.py`.

## Enabling / Disabling

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
