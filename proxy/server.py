"""Invisible driver: genuine `opencode` CLI exposed as an OpenAI-compatible API.

Hermes talks to this (provider=custom) and it forwards to the REAL opencode
binary, whose genuine client attribution unlocks the free muse-spark tier.
Hermes itself is 100% stock — nothing patched, nothing forked.

Endpoints: GET /v1/models, POST /v1/chat/completions (stream + non-stream).
Stdlib only.
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

MODEL = os.getenv("OPENCODE_MODEL", "opencode/muse-spark-1.3-contributor-free")
TIMEOUT = int(os.getenv("OPENCODE_TIMEOUT", "300"))


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


async def _run_opencode(prompt: str) -> str:
    binary = shutil.which("opencode")
    if not binary:
        raise RuntimeError("opencode binary not found")
    proc = await asyncio.create_subprocess_exec(
        binary, "run", "--model", MODEL, "--format", "json", prompt,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        raise RuntimeError(f"opencode timed out after {TIMEOUT}s")
    output = stdout.decode("utf-8", "ignore").strip()
    if not output:
        raise RuntimeError(stderr.decode("utf-8", "ignore").strip()[-500:] or "empty reply")
    reply = ""
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            reply = line
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else event
        part = data.get("part") or {}
        if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
            reply = part["text"]
        elif isinstance(data.get("text"), str):
            reply = data["text"]
        elif isinstance(data.get("result"), str):
            reply = data["result"]
    if not reply.strip():
        raise RuntimeError("could not parse opencode reply")
    return reply.strip()


def ask(prompt: str) -> str:
    """Run one opencode call from sync context."""
    return asyncio.run(_run_opencode(prompt))


class Handler(BaseHTTPRequestHandler):
    server_version = "opencode-proxy/1.0"

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
            self._send(200, {"object": "list", "data": [{
                "id": "muse-spark-1.3", "object": "model",
                "owned_by": "opencode", "created": int(time.time()),
            }]})
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
        try:
            reply = ask(_messages_to_prompt(req.get("messages", [])))
        except Exception as exc:  # noqa: BLE001
            log.warning("opencode call failed: %s", exc)
            self._send(502, {"error": {"type": "EngineError", "message": str(exc)[:300]}})
            return

        rid = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created = int(time.time())
        if req.get("stream"):
            chunks = [reply[i:i + 60] for i in range(0, len(reply), 60)] or [""]
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            for piece in chunks:
                frame = {"id": rid, "object": "chat.completion.chunk", "created": created,
                         "model": "muse-spark-1.3",
                         "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}]}
                self.wfile.write(f"data: {json.dumps(frame)}\n\n".encode())
            done = {"id": rid, "object": "chat.completion.chunk", "created": created,
                    "model": "muse-spark-1.3",
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
            self.wfile.write(f"data: {json.dumps(done)}\n\ndata: [DONE]\n\n".encode())
            return

        prompt_tokens = len(req.get("messages", [])) * 10
        self._send(200, {
            "id": rid, "object": "chat.completion", "created": created, "model": "muse-spark-1.3",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": reply},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": prompt_tokens,
                      "completion_tokens": len(reply) // 4, "total_tokens": prompt_tokens + len(reply) // 4},
        })


def main() -> None:
    """Start the proxy."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    port = int(os.getenv("OPENCODE_PROXY_PORT", "4096"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    log.info("opencode proxy on 127.0.0.1:%s model=%s", port, MODEL)
    server.serve_forever()


if __name__ == "__main__":
    main()
