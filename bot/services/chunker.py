"""Message chunking + MEMORY tag extraction."""
from __future__ import annotations

import re

MEMORY_RE = re.compile(r"\[MEMORY:\s*([^=\]]+)=([^\]]+)\]")


def extract_memory_tags(text: str) -> tuple[str, dict[str, str]]:
    """Remove ``[MEMORY: key=value]`` tags from text and return them.

    Args:
        text: Raw agent reply.

    Returns:
        Tuple of (clean_text, facts_dict).
    """
    facts: dict[str, str] = {}

    def _collect(match: re.Match[str]) -> str:
        facts[match.group(1).strip()] = match.group(2).strip()
        return ""

    clean = MEMORY_RE.sub(_collect, text).strip()
    return clean, facts


def split_chunks(text: str, size: int = 200) -> list[str]:
    """Split text into chunks of at most ``size`` chars, preferring line breaks.

    Args:
        text: The message text.
        size: Max chunk length.

    Returns:
        List of chunk strings.
    """
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in text.splitlines(keepends=True):
        if current_len + len(line) > size and current:
            chunks.append("".join(current).strip())
            current, current_len = [], 0
        if len(line) > size:  # hard-split very long single lines
            for i in range(0, len(line), size):
                part = line[i : i + size]
                if current_len + len(part) > size and current:
                    chunks.append("".join(current).strip())
                    current, current_len = [], 0
                current.append(part)
                current_len += len(part)
        else:
            current.append(line)
            current_len += len(line)
    if current:
        chunks.append("".join(current).strip())
    return [c for c in chunks if c]
