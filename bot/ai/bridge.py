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


async def ask_agent(
    user_id: int,
    prompt: str,
    *,
    serve_url: str,
    model: str,
    timeout: int = 180,
    allow_edit: bool = False,
) -> str:
    """Send a prompt to opencode and return the agent's reply text.

    Args:
        user_id: Telegram user id (used to isolate the opencode session).
        prompt: The full prompt (system + history + user message).
        serve_url: Base URL of the local ``opencode serve`` instance.
        model: Model id, e.g. ``opencode/muse-spark-1.3``.
        timeout: Max seconds to wait for the agent.
        allow_edit: Owner-only. When True, the agent may edit its own
            code (``--auto``) when the owner asks for changes.

    Returns:
        The agent's reply text, or an error message in Persian.
    """
    binary = shutil.which("opencode")
    if not binary:
        log.error("opencode binary not found")
        return "یه لحظه مشکلی پیش اومد، دوباره امتحان کن"

    cmd = [
        binary,
        "run",
        "--attach",
        serve_url,
        "--session",
        f"tg-{user_id}",
        "--model",
        model,
        "--format",
        "json",
    ]
    if allow_edit:
        cmd.append("--auto")
    cmd.append(prompt)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        log.warning("opencode timed out for user %s", user_id)
        return "یه کم طول کشید، دوباره بفرستش"
    except Exception:  # noqa: BLE001
        log.exception("opencode bridge failed")
        return "یه لحظه مشکلی پیش اومد، دوباره امتحان کن"

    output = stdout.decode("utf-8", "ignore").strip()
    if not output:
        err = stderr.decode("utf-8", "ignore").strip()[-300:]
        log.error("empty opencode reply: %s", err)
        return "یه لحظه مشکلی پیش اومد، دوباره امتحان کن"

    # ``--format json`` streams JSON events; the last text part wins.
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
        data = event.get("data") or event
        part = data.get("part") or {}
        if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
            reply = part["text"]
        elif isinstance(data, dict) and isinstance(data.get("text"), str):
            reply = data["text"]
    return reply.strip() or "یه لحظه مشکلی پیش اومد، دوباره امتحان کن"
