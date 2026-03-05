"""Example: OpenTelemetry tracing with omniwrap + omniray.

Auto-instruments your entire codebase with OpenTelemetry spans.
Requires: pip install omniray

Usage:
    # Console tree output only
    OMNIRAY_LOG=true python examples/otel_tracing.py

    # Console tree + OpenTelemetry spans
    OMNIRAY_LOG=true OMNIRAY_OTEL=true python examples/otel_tracing.py

    # With I/O logging (logs function arguments and return values)
    OMNIRAY_LOG=true OMNIRAY_LOG_INPUT=true OMNIRAY_LOG_OUTPUT=true python examples/otel_tracing.py

Environment variables:
    OMNIWRAP=true/false        - Enable/disable wrapping (when enabled=None)
    OMNIRAY_LOG=true           - Enable colored console tree output
    OMNIRAY_LOG_INPUT=true     - Log function arguments
    OMNIRAY_LOG_OUTPUT=true    - Log function return values
    OMNIRAY_LOG_COLOR=true     - Enable ANSI colors in console
    OMNIRAY_LOG_STYLE=auto     - Box-drawing style: unicode/ascii/auto
    OMNIRAY_OTEL=true          - Enable OpenTelemetry span creation
"""

from omniray import create_trace_wrapper, trace
from omniwrap import wrap_all

# --- Application code ---


def process_order(order_id: int) -> dict:
    """Process an order through validation and fulfillment."""
    validated = validate_order(order_id)
    if validated:
        return fulfill_order(order_id)
    return {"status": "invalid"}


def validate_order(order_id: int) -> bool:
    """Validate order exists and is payable."""
    return order_id > 0


def fulfill_order(order_id: int) -> dict:
    """Fulfill a validated order."""
    return {"order_id": order_id, "status": "fulfilled"}


# --- Selective OTel: spans only for critical functions, regardless of OMNIRAY_OTEL ---


@trace(otel=True, log_input=True)
def process_payment(order_id: int, amount: float) -> dict:
    """Process payment — always emits an OTel span even without OMNIRAY_OTEL=true."""
    return {"order_id": order_id, "amount": amount, "status": "paid"}


# --- Startup ---

if __name__ == "__main__":
    # Create trace wrappers for automatic instrumentation
    wrappers = create_trace_wrapper()

    # Wrap everything - one line, entire codebase gets tracing
    wrap_all(wrappers)

    # Every function call is now traced.
    # With OMNIRAY_LOG=true, you'll see a colored tree in the console:
    #
    # ┌─ process_order
    # ├─ ┌─ validate_order
    # │  └─ (0.01ms) validate_order
    # ├─ ┌─ fulfill_order
    # │  └─ (0.02ms) fulfill_order
    # └─ (0.15ms) process_order
    result = process_order(42)
    print(f"Order result: {result}")

    # process_payment has @trace(otel=True) — it always emits an OTel span,
    # even when OMNIRAY_OTEL is not set globally.
    payment = process_payment(42, 99.99)
    print(f"Payment result: {payment}")
