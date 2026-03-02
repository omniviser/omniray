"""Benchmark: measure per-call overhead of omniwrap wrapping.

Compares direct function calls vs wrapped calls to quantify overhead.

Usage:
    python benchmarks/bench_overhead.py
"""

import time
from types import ModuleType

import wrapt


def _noop_wrapper(wrapped, instance, args, kwargs):
    """Minimal wrapper — measures pure wrapt dispatch overhead."""
    return wrapped(*args, **kwargs)


def _timing_wrapper(wrapped, instance, args, kwargs):
    """Wrapper with timing — similar to omniray without OTel spans."""
    start = time.perf_counter()
    result = wrapped(*args, **kwargs)
    _ = time.perf_counter() - start
    return result


def target_function(a: int, b: int) -> int:
    """Cheap function to isolate wrapper overhead from actual work."""
    return a + b


def _bench(func, iterations: int) -> float:
    """Run func for `iterations` and return total seconds."""
    start = time.perf_counter()
    for _ in range(iterations):
        func(1, 2)
    return time.perf_counter() - start


def _wrap_function(func, wrapper):
    """Apply wrapper to a function using wrapt (same as omniwrap internally)."""
    module = ModuleType("_bench_module")
    module.target = func
    wrapt.wrap_function_wrapper(module, "target", wrapper)
    return module.target


def main() -> None:
    iterations = 1_000_000

    # Baseline: direct call
    baseline_s = _bench(target_function, iterations)
    baseline_ns = (baseline_s / iterations) * 1e9

    # No-op wrapper: pure wrapt dispatch
    noop_wrapped = _wrap_function(target_function, _noop_wrapper)
    noop_s = _bench(noop_wrapped, iterations)
    noop_ns = (noop_s / iterations) * 1e9

    # Timing wrapper: wrapt + perf_counter
    timing_wrapped = _wrap_function(target_function, _timing_wrapper)
    timing_s = _bench(timing_wrapped, iterations)
    timing_ns = (timing_s / iterations) * 1e9

    print(f"Iterations: {iterations:,}")
    print()
    print(f"{'Scenario':<30} {'Per call':>12} {'Overhead':>12}")
    print("-" * 56)
    print(f"{'Direct call (baseline)':<30} {baseline_ns:>9.0f} ns  {'—':>10}")
    print(f"{'No-op wrapper':<30} {noop_ns:>9.0f} ns  {noop_ns - baseline_ns:>+9.0f} ns")
    print(f"{'Timing wrapper':<30} {timing_ns:>9.0f} ns  {timing_ns - baseline_ns:>+9.0f} ns")
    print()
    print(
        f"Overhead per wrapped call: ~{noop_ns - baseline_ns:.0f} ns (no-op), "
        f"~{timing_ns - baseline_ns:.0f} ns (with timing)"
    )


if __name__ == "__main__":
    main()
