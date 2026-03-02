# omniwrap

Automatically wrap every function and method in your codebase with a single call.

See the [main README](../../README.md) for full documentation.

## Installation

```bash
pip install omniwrap
```

## Quick Start

```python
from omniwrap import wrap_all

def log_calls(wrapped, instance, args, kwargs):
    print(f"Calling {wrapped.__qualname__}")
    return wrapped(*args, **kwargs)

wrap_all(log_calls)
```

## License

Apache 2.0
