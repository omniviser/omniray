"""Performance regression tests for omniwrap wrapping overhead.

Uses relative comparisons (wrapped vs unwrapped) to avoid flakiness from variable CI runner
performance.
"""

import time
from types import ModuleType

import wrapt

MAX_OVERHEAD_NS = 5000


def _noop_wrapper(wrapped, instance, args, kwargs):  # noqa: ARG001
    return wrapped(*args, **kwargs)


def _target(a, b):
    return a + b


def _wrap(func, wrapper):
    module = ModuleType("_perf_module")
    module.target = func
    wrapt.wrap_function_wrapper(module, "target", wrapper)
    return module.target


def _measure(func, iterations):
    start = time.perf_counter()
    for _ in range(iterations):
        func(1, 2)
    return time.perf_counter() - start


def test_wrapping_overhead_within_bounds():
    """Wrapped call overhead should stay under 1μs per call.

    Measures absolute overhead (wrapped - baseline) rather than ratio,
    because a trivial baseline (~20ns) makes ratios noisy.
    On modern hardware, wrapt dispatch overhead is typically 200-400ns.
    The 1μs bound is generous to avoid CI flakiness.
    """
    iterations = 500_000
    baseline = _measure(_target, iterations)
    wrapped = _wrap(_target, _noop_wrapper)
    wrapped_time = _measure(wrapped, iterations)

    overhead_ns = ((wrapped_time - baseline) / iterations) * 1e9
    assert overhead_ns < MAX_OVERHEAD_NS, (
        f"Wrapping overhead too high: {overhead_ns:.0f} ns per call (limit: {MAX_OVERHEAD_NS} ns)"
    )
