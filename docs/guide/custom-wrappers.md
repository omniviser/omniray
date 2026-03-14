# Custom Wrappers

## How It Works

```
wrap_all(*wrappers)
  │
  ├─ Load config from pyproject.toml
  ├─ Discover all .py files in configured paths
  ├─ Import each module
  └─ For each function/method:
      ├─ Skip if: dunder, property, exception class, @skip_wrap, already wrapped
      ├─ Detect sync vs async
      └─ Apply wrapper via wrapt (safe monkey-patching)
```

## Writing a Wrapper

A wrapper is any callable with the [wrapt signature](https://wrapt.readthedocs.io/en/latest/wrappers.html):

```python
def my_wrapper(wrapped, instance, args, kwargs):
    # wrapped   - the original function
    # instance  - None for functions, self/cls for methods
    # args      - positional arguments
    # kwargs    - keyword arguments

    # ... do something before ...
    result = wrapped(*args, **kwargs)
    # ... do something after ...
    return result
```

For async functions, provide a separate async wrapper:

```python
async def my_async_wrapper(wrapped, instance, args, kwargs):
    result = await wrapped(*args, **kwargs)
    return result

wrap_all((my_wrapper, my_async_wrapper))
```

## Multiple Wrappers

First wrapper = innermost, closest to the original function:

```python
wrap_all(log_calls, (sync_trace, async_trace))
```

## Excluding Functions

Use `@skip_wrap` to exclude specific functions or classes:

```python
from omniwrap import skip_wrap

@skip_wrap
def healthcheck():
    return "ok"
```
