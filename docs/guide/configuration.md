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
| `OMNIRAY_LOG_INPUT_SIZE` | bool | unset | Append deep input size (MB) to the timing line. Uses `pympler.asizeof` — opt-in, can be slow on very large object graphs. |
| `OMNIRAY_LOG_OUTPUT_SIZE` | bool | unset | Append deep return-value size (MB) to the timing line. Same caveats as `LOG_INPUT_SIZE`. |
| `OMNIRAY_LOG_RSS` | bool | unset | Append process RSS (current MB, delta before→after, peak since process start) to the timing line. Current via `psutil`; peak via `resource.getrusage` (Unix). ~5–20µs per call. |
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

## Color Thresholds

Each segment of the trace line (duration, size, RSS) is color-coded by value: **DIM → GREEN → YELLOW → RED**. Tune the boundaries and the `[BIG]`/`[SLOW]` tag cutoffs under `[tool.omniray]` in your `pyproject.toml`:

```toml
[tool.omniray]
size = [0.1, 1, 10]              # MB: IN/OUT payload (DIM < 0.1, GREEN < 1, YELLOW < 10, RED ≥ 10)
rss = [100, 500, 1000]           # MB: RSS current / peak
rss_delta = [1, 10, 100]         # MB: RSS delta (negative / near-zero → DIM)
duration_ms = [1, 10, 100]       # ms: span duration boundaries
size_big_tag_mb = 10             # MB: IN/OUT size at/above which the `[BIG]` tag is appended
duration_slow_tag_ms = 200       # ms: duration at/above which the `[SLOW]` tag is appended
compact = true                   # bool: collapse repeated leaf-call siblings into one summary line
compact_threshold = 3            # int (≥ 2): minimum repetitions required to emit a summary
```

All keys are optional — omitted ones fall back to the defaults shown above. The file is resolved by walking up from the current working directory until the first `pyproject.toml` is found; missing or malformed files cause silent fallback to defaults (tracing must never break the host app). Thresholds are loaded once at import time; restart the process to pick up changes.

!!! note "Built-in exclusions"

    Always applied: `.venv`, `__pycache__`, `.git`, `.hg`, `.pytest_cache`, `__init__.py`, `__main__.py`, `asgi.py`, `wsgi.py`.

## Streak Compaction

When several consecutive sibling calls share the same span name and have no nested children logged between them, omniray collapses them into a single summary line instead of emitting one start/end pair per call. Typical trigger: a hot loop calling the same helper many times.

**Without compaction** (28 calls — 28 separate entries flood the trace):

```
┌─ AzureFunc.post
└─ (75.95ms, in: 0.35MB, rss: 124.20MB) AzureFunc.post

┌─ AzureFunc.post
└─ (0.01ms, in: 0.35MB, rss: 124.20MB) AzureFunc.post

… (26 more identical lines) …
```

**With compaction** (one summary collapses the streak):

```
┌─ AzureFunc.post
└─ x28 AzureFunc.post
     time: Σ75.96ms, μ2.713ms, max 75.95ms
     memory: Σin: 9.80MB, rss: 124.20MB, Σ+0.05MB, peak: 277.62MB
```

The count marker (`x28`) is always rendered in **bright red** because repetition itself is a perf signal — a single 76ms cold call with 27 cache hits is invisible without aggregation, and the disparity between `μ` (mean) and `max` exposes the outlier.

**A streak flushes** (summary emits) when:

- A different span name appears at the same depth (sibling break).
- The parent of the streak exits (depth shrinks).
- An error is logged at the same depth — failures are never masked.

**Configuration:**

| Key | Default | Effect |
|-----|---------|--------|
| `compact` | `true` | Master toggle. Set `false` to keep legacy per-call rendering. |
| `compact_threshold` | `3` | Streak must reach this count before collapsing. Below threshold, calls render individually with average duration. |

Set `compact_threshold = 10` to compact only large floods (e.g. data-pipeline projects); set `compact_threshold = 2` to collapse even pairs.

**When extras are configured** (`size`, `rss` flags on), the `memory:` continuation line aggregates: `Σin/Σout` sum across the streak, `rss` is the maximum observed current-RSS, `peak` is the maximum kernel-reported peak, and the signed `Σ` delta sums net memory pressure. With those flags off, the line is omitted and only `time:` is shown.

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
