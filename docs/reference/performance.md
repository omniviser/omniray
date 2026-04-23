# Performance

## omniwrap

omniwrap uses [wrapt](https://github.com/GrahamDumpleton/wrapt) for monkey-patching, which adds a small per-call overhead. Measured on Apple M4, Python 3.13:

| Scenario | Per call | Overhead |
|----------|----------|----------|
| Direct call (baseline) | ~15 ns | — |
| Wrapped (no-op wrapper) | ~250 ns | **~235 ns** |
| Wrapped (with timing) | ~325 ns | ~310 ns |

**~200-300 ns per wrapped call.** A typical web request with 200 wrapped calls adds ~50 us — less than 0.01% of a 500ms response. A single database query (~5 ms) costs as much as ~20,000 wrapped calls.

## omniray

omniray adds per-call overhead on top of omniwrap. Measured on Apple M4, Python 3.14:

| Scenario | Per call | Overhead |
|----------|----------|----------|
| Tracing wired, all flags off | ~1.0 us | **~1 us** |
| `OMNIRAY_LOG=true` (console output) | ~17 us | **~17 us** |
| `OMNIRAY_LOG=true` + `LOG_INPUT` + `LOG_OUTPUT` | ~45 us | **~45 us** |

### Where the time goes

- **Flags off** (~1 us) — flag resolution, span name generation, two `time.time()` calls, and ContextVar bookkeeping.
- **Console logging** (~17 us) — Python's `logging` module: 3x `logger.info()` per call, each acquiring a thread lock, formatting the tree structure, and writing to stderr. Unlike post-mortem profilers that defer display to the end, omniray formats output **live per call**.
- **I/O logging** (~45 us) — serializes arguments and return values via `pydantic_core.to_jsonable_python()` + `json.dumps()`. Designed for selective use on specific functions via `@trace(log_input=True)`.
- **RSS logging** (+5–20 us) — `psutil` for current RSS, `resource.getrusage` for peak (Unix). Fixed cost; safe to leave on broadly.
- **OpenTelemetry spans** (`OMNIRAY_OTEL`) — creates and closes an OTel span, sets attributes. Cost depends on your exporter and span processor.

A typical debugging session tracing **50** function calls per request adds **~0.8 ms** with console logging.

!!! warning "Payload size profiling is unbounded"

    `OMNIRAY_LOG_INPUT_SIZE` / `OMNIRAY_LOG_OUTPUT_SIZE` use [`pympler.asizeof`](https://pympler.readthedocs.io/en/latest/library/asizeof.html) to measure **deep** object graph size. Unlike the microsecond-scale overheads above, this scales with the size and complexity of your inputs and return values — it can take **milliseconds or more** on large nested structures (big DataFrames, ORM result sets, numpy arrays with Python-object dtype, deeply recursive graphs).


## Run Benchmarks

```bash
python benchmarks/bench_overhead.py           # omniwrap wrapping overhead
python benchmarks/bench_tracer_overhead.py    # omniray tracing overhead
```
