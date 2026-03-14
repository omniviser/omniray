# @trace Decorator

Use `@trace` for manual per-function instrumentation. For automatic instrumentation of your entire codebase, use `create_trace_wrapper()` with `wrap_all()` instead.

```python
from omniray import trace

@trace(
    log=None,         # Override OMNIRAY_LOG per-function
    log_input=None,   # Override OMNIRAY_LOG_INPUT per-function
    log_output=None,  # Override OMNIRAY_LOG_OUTPUT per-function
    skip_if=None,     # Predicate: skip tracing when True
    otel=None,        # Override OMNIRAY_OTEL per-function
)
def my_function(): ...
```

## I/O Logging

```python
@trace(log_input=True, log_output=True)
def send_message(conversation_id: str, content: str, mode: str): ...
```

```
14:23  INFO: ┌─ ChatService.send_message
14:23  INFO: IN: {
14:23  INFO:   "conversation_id": "8467faba-378e-43e1-a757-970df1e05f1f",
14:23  INFO:   "content": "who is the president of France?",
14:23  INFO:   "mode": "web_search"
14:23  INFO: }
14:23  INFO: │  ├─ ┌─ SearchProvider.web_search
14:23  INFO: │  │  └─ (2737.41ms) SearchProvider.web_search [SLOW]
14:23  INFO: │  ├─ ┌─ SearchResult.extract_sources
14:23  INFO: │  │  └─ (0.32ms) SearchResult.extract_sources
14:23  INFO: │  ├─ ┌─ Message.to_schema
14:23  INFO: │  │  ├─ ┌─ Source.to_schema
14:23  INFO: │  │  │  └─ (0.08ms) Source.to_schema
14:23  INFO: │  │  ├─ ┌─ Source.to_schema
14:23  INFO: │  │  │  └─ (0.01ms) Source.to_schema
14:23  INFO: │  │  └─ (133.96ms) Message.to_schema
14:23  INFO: │  └─ (4095.51ms) ChatService.send_message [SLOW]
14:23  INFO: OUT: {
14:23  INFO:   "id": "2fda24e1-fb2f-428d-a9c5-16361fd1f049",
14:23  INFO:   "content": "The current president of France is Emmanuel Macron.",
14:23  INFO:   "sources": [{"title": "...", "url": "..."}, ...],
14:23  INFO:   "mode": "web_search"
14:23  INFO: }
14:23  INFO: └─ (4460.29ms) ChatService.send_message [SLOW]
```

!!! warning "Secrets in logs"

    `log_input` and `log_output` serialize function arguments and return values to the console. Make sure your secrets are properly protected — e.g. stored in Pydantic's `SecretStr`, which redacts values in `repr()` and JSON output. Plain `str` passwords or API keys **will** appear in your logs.

You can also enable I/O logging globally via environment variables (not recommended — prefer `@trace` on specific functions):

```bash
OMNIRAY_LOG=true OMNIRAY_LOG_INPUT=true OMNIRAY_LOG_OUTPUT=true python app.py
```

## Conditional Skip

```python
@trace(skip_if=lambda path, **kw: path == "/healthz")
def handle_request(path: str, method: str): ...
```

When `skip_if` returns `True`, tracing is bypassed entirely and the function is called directly.

## Selective OpenTelemetry

You don't have to choose between "OTel everywhere" and "OTel nowhere". Use `@trace(otel=True)` to create spans only for the functions that matter:

```python
@trace(otel=True)
def process_payment(order_id: str) -> bool: ...

@trace(otel=True, log_input=True)
async def call_external_api(endpoint: str, payload: dict) -> Response: ...
```

This works independently of `OMNIRAY_OTEL`. Even with `OMNIRAY_OTEL` unset globally, functions with `otel=True` will emit spans. Conversely, `OMNIRAY_OTEL=false` acts as a kill switch and disables spans everywhere — including per-function overrides.

## Double-Wrapping Prevention

Functions decorated with `@trace` are automatically excluded from `wrap_all()` instrumentation. You can safely use both `@trace` (for per-function config) and `wrap_all(create_trace_wrapper())` (for everything else) in the same codebase.
