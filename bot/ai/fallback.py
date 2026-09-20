"""OpenAI-compatible fallback backend (used when AI_BACKEND=openai)."""
from __future__ import annotations

import logging

log = logging.getLogger("parham.fallback")


async def ask_openai(
    system: str,
    history: list[dict[str, str]],
    message: str,
    *,
    api_key: str,
    base_url: str,
    model: str,
) -> str:
    """Ask an OpenAI-compatible endpoint.

    Args:
        system: System prompt.
        history: Recent ``{"role": ..., "content": ...}`` messages.
        message: The current user message.
        api_key: API key.
        base_url: Base URL of the API.
        model: Model id.

    Returns:
        The assistant reply text.
    """
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    messages = [{"role": "system", "content": system}]
    messages += history
    messages.append({"role": "user", "content": message})
    try:
        resp = await client.chat.completions.create(model=model, messages=messages)
        return (resp.choices[0].message.content or "").strip()
    except Exception:  # noqa: BLE001
        log.exception("openai fallback failed")
        return "یه لحظه مشکلی پیش اومد، دوباره امتحان کن"
    finally:
        await client.close()
