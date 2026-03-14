"""BIG RED BUTTON — omniray demo.

Run:
    OMNIRAY_LOG=true python -m examples.big_red_button
"""

from omniray import create_trace_wrapper
from omniwrap import wrap_all

wrap_all(create_trace_wrapper())

from examples.big_red_button.launch import BigRedButton  # noqa: E402

button = BigRedButton()
result = button.press()
print(f"\n💥 {result}")
