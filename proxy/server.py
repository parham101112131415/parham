"""Invisible driver: genuine `opencode` CLI exposed as an OpenAI-compatible API.

Hermes talks to this (provider=custom) and it forwards to the REAL opencode
binary, whose genuine client attribution unlocks the free muse-spark tier.
Hermes itself is 100% stock — nothing patched, nothing forked.

Endpoints: GET /v1/models, POST /v1/chat/completions (stream + non-stream).
Stdlib only. Text streams to the client AS opencode produces it, so the
Hermes stale-watchdog sees continuous output on long jobs.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("opencode-proxy")

# Hermes-facing id -> real opencode model id. /model switches between these.
MODEL_MAP = {
    "muse-spark-1.3": os.getenv("OPENCODE_MODEL", "opencode/muse-spark-1.3-contributor-free"),
    "muse-spark-1.3-free": "opencode/muse-spark-1.3-contributor-free",
    "mimo-v2.5-free": "opencode/mimo-v2.5-free",
}
TIMEOUT = int(os.getenv("OPENCODE_TIMEOUT", "900"))


def _messages_to_prompt(messages: list[dict]) -> str:
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):  # content blocks
            content = " ".join(
                b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
            )
        parts.append(f"{role.upper()}: {content}")
    parts.append("ASSISTANT:")
    return "\n\n".join(parts)


def _event_text(line: str) -> str:
    """Extract cumulative assistant text from one opencode JSON event line."""
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return ""
    data = event.get("data") if isinstance(event.get("data"), dict) else event
    if not isinstance(data, dict):
        return ""
    part = data.get("part") or {}
    if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
        return part["text"]
    return ""


async def _run_streaming(prompt: str, model: str, on_delta) -> str:
    """Run opencode, calling on_delta(new_text_suffix) live. Returns full text."""
    binary = shutil.which("opencode")
    if not binary:
        raise RuntimeError("opencode binary not found")
    proc = await asyncio.create_subprocess_exec(
        binary, "run", "--model", model, "--format", "json", prompt,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    full = ""
    try:
        assert proc.stdout is not None
        while True:
            try:
                raw = await asyncio.wait_for(proc.stdout.readline(), timeout=TIMEOUT)
            except asyncio.TimeoutError:
                raise RuntimeError(f"opencode silent for {TIMEOUT}s")
            if not raw:
                break
            line = raw.decode("utf-8", "ignore").strip()
            if not line:
                continue
            if line.startswith("{"):
                text = _event_text(line)
                if text and text.startswith(full):
                    suffix = text[len(full):]
                    if suffix:
                        full = text
                        on_delta(suffix)
                elif text and not full:
                    full = text
                    on_delta(text)
            else:
                full += (("\n" if full else "") + line)
                on_delta(line)
        await asyncio.wait_for(proc.wait(), timeout=30)
    finally:
        if proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
    if proc.returncode != 0 and not full.strip():
        err = (await proc.stderr.read()).decode("utf-8", "ignore").strip()[-500:]
        raise RuntimeError(err or f"opencode exit {proc.returncode}")
    if not full.strip():
        raise RuntimeError("empty reply from opencode")
    return full.strip()


def _run_blocking(prompt: str, model: str, on_delta) -> str:
    return asyncio.run(_run_streaming(prompt, model, on_delta))


class Handler(BaseHTTPRequestHandler):
    server_version = "opencode-proxy/2.0"

    def log_message(self, *args):  # keep logs clean
        pass

    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        """Serve the model list."""
        if self.path.rstrip("/").endswith("/models") or self.path == "/v1/models":
            now = int(time.time())
            self._send(200, {"object": "list", "data": [
                {"id": mid, "object": "model", "owned_by": "opencode", "created": now}
                for mid in MODEL_MAP
            ]})
        elif self.path in ("/health", "/api/health"):
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        """Serve chat completions (streaming + non-streaming)."""
        if not self.path.rstrip("/").endswith("/chat/completions"):
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length) or b"{}")
        except Exception:  # noqa: BLE001
            self._send(400, {"error": "bad request"})
            return
        wanted = req.get("model") or "muse-spark-1.3"
        model = MODEL_MAP.get(wanted, MODEL_MAP["muse-spark-1.3"])
        prompt = _messages_to_prompt(req.get("messages", []))
        t0 = time.monotonic()
        n_msgs = len(req.get("messages", []))
        log.info("req model=%s->%s msgs=%d prompt_chars=%d stream=%s",
                 wanted, model, n_msgs, len(prompt), bool(req.get("stream")))

        rid = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created = int(time.time())
        try:
            if req.get("stream"):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()

                def _emit(piece: str) -> None:
                    frame = {"id": rid, "object": "chat.completion.chunk",
                             "created": created, "model": wanted,
                             "choices": [{"index": 0, "delta": {"content": piece},
                                          "finish_reason": None}]}
                    self.wfile.write(f"data: {json.dumps(frame)}\n\n".encode())
                    self.wfile.flush()

                reply = _run_blocking(prompt, model, _emit)
                done = {"id": rid, "object": "chat.completion.chunk",
                        "created": created, "model": wanted,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
                self.wfile.write(f"data: {json.dumps(done)}\n\ndata: [DONE]\n\n".encode())
                log.info("stream done %.1fs chars=%d", time.monotonic() - t0, len(reply))
                return

            chunks: list[str] = []
            reply = _run_blocking(prompt, model, chunks.append)
            prompt_tokens = len(prompt) // 4
            self._send(200, {
                "id": rid, "object": "chat.completion", "created": created,
                "model": wanted,
                "choices": [{"index": 0,
                             "message": {"role": "assistant", "content": reply},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": prompt_tokens,
                          "completion_tokens": len(reply) // 4,
                          "total_tokens": prompt_tokens + len(reply) // 4},
            })
            log.info("done %.1fs chars=%d", time.monotonic() - t0, len(reply))
        except (ConnectionError, BrokenPipeError):
            log.info("client went away after %.1fs", time.monotonic() - t0)
        except Exception as exc:  # noqa: BLE001
            log.warning("opencode call failed after %.1fs: %s", time.monotonic() - t0, exc)
            try:
                self._send(502, {"error": {"type": "EngineError",
                                           "message": str(exc)[:300]}})
            except (ConnectionError, BrokenPipeError):
                pass


def main() -> None:
    """Start the proxy."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    port = int(os.getenv("OPENCODE_PROXY_PORT", "4096"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    log.info("opencode proxy on 127.0.0.1:%s models=%s", port, ",".join(MODEL_MAP))
    server.serve_forever()


if __name__ == "__main__":
    main()
