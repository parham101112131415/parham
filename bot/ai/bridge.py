"""Bridge backend: forward user messages to the local opencode agent (Muse Spark).

Each Telegram user maps to a persistent opencode session (``tg-<id>``),
exactly like a Hermes gateway channel: isolated memory per user, full
tool access inside opencode.
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil

log = logging.getLogger("parham.bridge")

GENERIC_ERROR = "یه لحظه مشکلی پیش اومد، دوباره امتحان کن"


async def _exec(cmd: list[str], timeout: int) -> str:
    """Run an opencode command, return stdout or raise RuntimeError(stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        raise RuntimeError("timeout after %ss" % timeout)
    output = stdout.decode("utf-8", "ignore").strip()
    if not output:
        err = stderr.decode("utf-8", "ignore").strip()[-500:] or f"exit {proc.returncode}"
        raise RuntimeError(err)
    return output


def _parse_reply(output: str) -> str:
    """Extract the reply text from ``--format json`` event stream (or plain text)."""
    reply = ""
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
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
    return reply.strip()


async def ask_agent(
    user_id: int,
    prompt: str,
    *,
    serve_url: str,
    model: str,
    timeout: int = 180,
    allow_edit: bool = False,
    error_log: str | None = None,
) -> str:
    """Send a prompt to opencode and return the agent's reply text.

    Tries the persistent attached session first (``--attach``), then falls
    back to a standalone run. Raises RuntimeError if both fail.

    Args:
        user_id: Telegram user id (used to isolate the opencode session).
        prompt: The full prompt (system + history + user message).
        serve_url: Base URL of the local ``opencode serve`` instance.
        model: Model id, e.g. ``opencode/muse-spark-1.3``.
        timeout: Max seconds to wait for the agent.
        allow_edit: Owner-only ``--auto`` flag for self-modification.
        error_log: Optional file path where the last stderr is stored
            for the /status diagnostic.

    Returns:
        The agent's reply text.

    Raises:
        RuntimeError: When opencode fails (message = human-readable cause).
    """
    binary = shutil.which("opencode")
    if not binary:
        raise RuntimeError("opencode binary not found on PATH")

    base = [binary, "run", "--model", model, "--format", "json"]
    if allow_edit:
        base.append("--auto")

    attempts = [
        base + ["--attach", serve_url, "--session", f"tg-{user_id}", prompt],
        base + ["--session", f"tg-{user_id}", prompt],
    ]
    last_err = "unknown"
    for i, cmd in enumerate(attempts):
        try:
            output = await _exec(cmd, timeout)
        except RuntimeError as exc:
            last_err = str(exc)
            log.warning("opencode attempt %d failed for user %s: %s", i + 1, user_id, last_err)
            continue
        reply = _parse_reply(output)
        if reply:
            return reply
        last_err = "empty reply: " + output[-300:]
        log.warning("opencode attempt %d empty for user %s", i + 1, user_id)

    if error_log:
        try:
            with open(error_log, "w") as fh:
                fh.write(last_err)
        except OSError:
            pass
    raise RuntimeError(last_err)
