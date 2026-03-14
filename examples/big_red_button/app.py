"""BIG RED BUTTON — omniray web demo.

Run:
    OMNIRAY_LOG=true uvicorn examples.big_red_button.app:app --reload
"""

import asyncio
import json
import logging
import queue
import re
import threading

from omniray import create_trace_wrapper
from omniwrap import wrap_all

wrap_all(create_trace_wrapper())

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402
from starlette.responses import StreamingResponse  # noqa: E402

from examples.big_red_button.launch import BigRedButton  # noqa: E402

app = FastAPI()

ANSI_TO_CSS = {
    "0": "",
    "1": "font-weight:bold",
    "2": "opacity:0.5",
    "31": "color:#cc0000",
    "32": "color:#00aa00",
    "33": "color:#aa8800",
    "34": "color:#0000cc",
    "35": "color:#aa00aa",
    "36": "color:#00aaaa",
    "37": "color:#aaaaaa",
    "90": "color:#888",
    "91": "color:#ff4444",
    "92": "color:#44ff44",
    "93": "color:#ffff44",
}


def ansi_to_html(text: str) -> str:
    """Convert ANSI escape codes to HTML spans.

    All text content is escaped to prevent XSS — only our own
    controlled <span style="..."> tags are injected.
    """
    result = []
    parts = re.split(r"\x1b\[([0-9;]*)m", text)
    open_spans = 0
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Escape all user-visible text to prevent XSS
            result.append(part.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        elif part in {"0", ""}:
            result.append("</span>" * open_spans)
            open_spans = 0
        else:
            styles = [ANSI_TO_CSS[code] for code in part.split(";") if ANSI_TO_CSS.get(code)]
            if styles:
                result.append(f'<span style="{";".join(styles)}">')
                open_spans += 1
    result.append("</span>" * open_spans)
    return "".join(result)


class QueueHandler(logging.Handler):
    """Logging handler that puts formatted records into a queue."""

    def __init__(self, q: queue.Queue) -> None:
        super().__init__()
        self.q = q

    def emit(self, record: logging.LogRecord) -> None:
        self.q.put(self.format(record))


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>BIG RED BUTTON — omniray demo</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #c8c8c8;
            color: #222;
            font-family: system-ui, -apple-system, sans-serif;
            display: flex;
            height: 100vh;
        }
        .left {
            width: 40%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border-right: 1px solid #ddd;
            padding: 40px;
        }
        .right {
            width: 60%;
            display: flex;
            flex-direction: column;
            padding: 20px;
        }
        h1 { font-size: 1.8rem; margin-bottom: 8px; }
        .subtitle { color: #888; margin-bottom: 30px; }
        #boom-btn {
            background: #cc0000;
            color: white;
            border: none;
            width: 160px;
            height: 160px;
            border-radius: 50%;
            font-size: 1rem;
            font-weight: 700;
            cursor: pointer;
        }
        #boom-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .trace-header {
            color: #000;
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        #trace-output {
            flex: 1;
            background: #f5f5f5;
            border: 1px solid #ddd;
            padding: 16px;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 0.85rem;
            line-height: 1.6;
            overflow: auto;
            color: #444;
        }
        #trace-output pre { margin: 0; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="left">
        <button id="boom-btn" onclick="pressButton()">BIG RED BUTTON</button>
    </div>
    <div class="right">
        <div class="trace-header">omniray trace output</div>
        <div id="trace-output"><pre id="trace-pre">Waiting for button press...</pre></div>
    </div>

    <script>
        async function pressButton() {
            const btn = document.getElementById('boom-btn');
            const pre = document.getElementById('trace-pre');
            const boom = document.getElementById('boom-text');

            btn.disabled = true;
            pre.textContent = '';

            const evtSource = new EventSource('/press-stream');

            evtSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'trace') {
                    // Safe: html is generated server-side from our own trace output
                    // with all text content escaped via ansi_to_html()
                    const line = document.createElement('div');
                    line.innerHTML = data.html;  // nosec: controlled server-side output
                    pre.appendChild(line);
                    pre.parentElement.scrollTop = pre.parentElement.scrollHeight;
                } else if (data.type === 'done') {
                    btn.disabled = false;
                    evtSource.close();
                }
            };

            evtSource.onerror = function() {
                btn.disabled = false;
                evtSource.close();
            };
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@app.get("/press-stream")
async def press_stream():
    q: queue.Queue[str | None] = queue.Queue()
    handler = QueueHandler(q)
    handler.setFormatter(
        logging.Formatter("%(asctime)s  %(levelname)s: %(message)s", datefmt="%H:%M")
    )
    logger = logging.getLogger("omniray.tracing")
    logger.addHandler(handler)

    def run_launch():
        button = BigRedButton()
        button.press()
        q.put(None)  # sentinel

    thread = threading.Thread(target=run_launch)

    async def event_generator():
        http_log = 'INFO:     127.0.0.1:53343 - "POST /explode HTTP/1.1" 200 OK'
        yield f"data: {json.dumps({'type': 'trace', 'html': ansi_to_html(http_log)})}\n\n"
        yield f"data: {json.dumps({'type': 'trace', 'html': '&nbsp;'})}\n\n"
        await asyncio.sleep(0.3)
        thread.start()

        while True:
            try:
                line = q.get(timeout=0.05)
            except queue.Empty:
                await asyncio.sleep(0.02)
                continue

            if line is None:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break

            stripped = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
            if not stripped or re.fullmatch(r"\d{2}:\d{2}\s+INFO:\s*", stripped):
                continue
            html_line = ansi_to_html(line)
            yield f"data: {json.dumps({'type': 'trace', 'html': html_line})}\n\n"

        logger.removeHandler(handler)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
