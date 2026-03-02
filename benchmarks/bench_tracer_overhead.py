"""Benchmark: per-call overhead of Tracer.trace() with OMNIRAY_LOG enabled.

Measures overhead across 5 scenarios — from bare Python call to full IO logging
with a StreamHandler active (not NullHandler).

Usage:
    cd oss/omniray
    python benchmarks/bench_tracer_overhead.py
"""

import os
import statistics
import sys
import time

# --- Import omniray modules (before patching module-level names) ---
import omniray.tracing.flags as flags_mod
from omniray.tracing.console import logger, setup_console_handler
from omniray.tracing.tracers import Tracer

RUNS = 7
WARMUP = 1_000


def target_function(a: int, b: int) -> int:
    """Cheap function to isolate tracer overhead from actual work."""
    return a + b


def _measure(call, iterations, runs):
    """Run call() in a tight loop, return (mean, median, stddev, min) in µs per call."""
    samples = []
    for _ in range(runs):
        start = time.perf_counter_ns()
        for _ in range(iterations):
            call()
        elapsed_ns = time.perf_counter_ns() - start
        samples.append(elapsed_ns / iterations / 1_000)  # ns → µs
    return (
        statistics.mean(samples),
        statistics.median(samples),
        statistics.stdev(samples) if len(samples) > 1 else 0.0,
        min(samples),
    )


def _setup_flags(*, log, log_input, log_output):
    """Patch module-level flags and clear the cached TraceFlags singleton."""
    flags_mod.CONSOLE_LOG_FLAG = log
    flags_mod.LOG_INPUT_FLAG = log_input
    flags_mod.LOG_OUTPUT_FLAG = log_output
    flags_mod._default_flags_cache.clear()  # noqa: SLF001


def _ensure_handler():
    """Install StreamHandler if absent, return it."""
    setup_console_handler()
    return logger.handlers[0]


def _warmup(call, n=WARMUP):
    for _ in range(n):
        call()


def main():
    results = []

    # ── 1. Bare function call (baseline) ──────────────────────────────────
    def s1():
        return target_function(1, 2)

    _warmup(s1)
    mean, median, std, mn = _measure(s1, 500_000, RUNS)
    results.append(("1. Bare function call", 500_000, mean, median, std, mn))
    baseline_min = mn

    # ── 2. Tracer.trace, all flags off ────────────────────────────────────
    _setup_flags(log=None, log_input=None, log_output=None)

    def s2():
        return Tracer.trace(target_function, (1, 2), {}, otel=False)

    _warmup(s2)
    mean, median, std, mn = _measure(s2, 200_000, RUNS)
    results.append(("2. Tracer.trace, flags off", 200_000, mean, median, std, mn))

    # ── 3. LOG=true, handler → /dev/null ──────────────────────────────────
    _setup_flags(log=True, log_input=None, log_output=None)
    handler = _ensure_handler()
    devnull = open(os.devnull, "w")  # noqa: SIM115, PTH123
    handler.stream = devnull

    def s3():
        return Tracer.trace(target_function, (1, 2), {}, otel=False)

    _warmup(s3)
    mean, median, std, mn = _measure(s3, 50_000, RUNS)
    results.append(("3. LOG=true, /dev/null", 50_000, mean, median, std, mn))

    # ── 4. LOG=true, handler → real stderr ────────────────────────────────
    handler.stream = sys.stderr

    def s4():
        return Tracer.trace(target_function, (1, 2), {}, otel=False)

    _warmup(s4, n=100)
    mean, median, std, mn = _measure(s4, 10_000, RUNS)
    results.append(("4. LOG=true, real stderr", 10_000, mean, median, std, mn))
    handler.stream = devnull  # silence output for the rest

    # ── 5. Full IO logging (LOG+INPUT+OUTPUT), /dev/null ──────────────────
    _setup_flags(log=True, log_input=True, log_output=True)

    def s5():
        return Tracer.trace(target_function, (1, 2), {}, otel=False)

    _warmup(s5, n=100)
    mean, median, std, mn = _measure(s5, 10_000, RUNS)
    results.append(("5. Full IO logging, /dev/null", 10_000, mean, median, std, mn))

    devnull.close()

    # ── Report ────────────────────────────────────────────────────────────
    cols = (
        f"{'Scenario':<38} {'Iters':>7}  {'Mean µs':>9} {'Med µs':>8}"
        f" {'Std µs':>8} {'Min µs':>8} {'Delta':>10}"
    )
    print()
    print(cols)
    print("-" * len(cols))
    for label, iters, mean, median, std, mn in results:
        delta = "—" if label.startswith("1.") else f"+{mn - baseline_min:.2f}"
        row = (
            f"{label:<38} {iters:>7,}  {mean:>9.2f} {median:>8.2f}"
            f" {std:>8.2f} {mn:>8.2f} {delta:>10}"
        )
        print(row)
    print()
    print(f"Runs per scenario: {RUNS} (delta = min - baseline min, per timeit convention)")
    print(f"Platform: {sys.platform}, Python {sys.version.split()[0]}")


if __name__ == "__main__":
    main()
