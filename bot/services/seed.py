"""Seed restore: layer the two Hermes backups onto DATA_DIR (newer wins).

Order:
  1. ``migrate-full.tar.xz`` — full ``.hermes/`` snapshot (base).
  2. ``hermes-memory-*.tgz`` — memory overlay (newer, wins on conflict).

Runtime junk (pid/lock/log/heartbeat/cache) is never restored.
"""
from __future__ import annotations

import logging
import os
import tarfile

log = logging.getLogger("parham.seed")

SKIP_SUFFIXES = (".pid", ".lock", ".log", ".heartbeat")
SKIP_PARTS = {"__pycache__", "cache", ".git"}


def _should_skip(name: str) -> bool:
    parts = name.split("/")
    if any(p in SKIP_PARTS for p in parts):
        return True
    return name.endswith(SKIP_SUFFIXES)


def _safe_extract(archive: str, dest: str) -> int:
    """Extract a tar archive into dest, skipping junk. Returns file count."""
    count = 0
    with tarfile.open(archive, "r:*") as tar:
        members = [m for m in tar.getmembers() if not _should_skip(m.name)]
        for member in members:
            # Prevent path traversal
            target = os.path.realpath(os.path.join(dest, member.name))
            if not target.startswith(os.path.realpath(dest) + os.sep):
                continue
        tar.extractall(dest, members=members, filter="data")
        count = len(members)
    return count


def find_archives(seed_dir: str) -> tuple[str | None, str | None]:
    """Find (migrate_full, memory_overlay) archives in seed_dir."""
    full = overlay = None
    if not os.path.isdir(seed_dir):
        return None, None
    for name in sorted(os.listdir(seed_dir)):
        lower = name.lower()
        path = os.path.join(seed_dir, name)
        if lower.startswith("migrate-full") and lower.endswith((".tar.xz", ".tgz", ".tar.gz")):
            full = path
        elif lower.startswith("hermes-memory") and lower.endswith((".tgz", ".tar.gz", ".tar.xz")):
            overlay = path
    return full, overlay


def seed_if_needed(data_dir: str, seed_dir: str) -> bool:
    """Restore seed archives into data_dir on first run.

    Args:
        data_dir: Railway volume dir (e.g. ``/data``).
        seed_dir: Dir holding the two Hermes archives.

    Returns:
        True if a seed was applied.
    """
    marker = os.path.join(data_dir, ".seeded")
    if os.path.exists(marker):
        return False
    full, overlay = find_archives(seed_dir)
    if not full and not overlay:
        log.info("no seed archives in %s, skipping", seed_dir)
        return False
    os.makedirs(data_dir, exist_ok=True)
    if full:
        log.info("seeding base: %s", full)
        _safe_extract(full, data_dir)
    if overlay:
        log.info("seeding overlay (newer wins): %s", overlay)
        _safe_extract(overlay, data_dir)
    with open(marker, "w") as fh:
        fh.write("seeded\n")
    log.info("seed complete")
    return True
