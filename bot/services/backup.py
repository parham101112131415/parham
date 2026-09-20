"""Full backup: pack DATA_DIR into a timestamped tar.xz (with secrets, no password).

Only the owner receives it (Telegram DM) + one copy stays on the volume.
"""
from __future__ import annotations

import datetime
import logging
import os
import tarfile

log = logging.getLogger("parham.backup")

SKIP_SUFFIXES = (".pid", ".lock", ".log", ".heartbeat")
SKIP_PARTS = {"__pycache__", "cache", ".git"}


def _should_skip(path: str) -> bool:
    parts = path.split(os.sep)
    if any(p in SKIP_PARTS for p in parts):
        return True
    return path.endswith(SKIP_SUFFIXES)


def create_backup(data_dir: str) -> str:
    """Create ``full-backup-YYYYMMDD-HHMMSS.tar.xz`` under ``data_dir/backups``.

    Args:
        data_dir: Railway volume dir.

    Returns:
        Absolute path of the created archive.
    """
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(data_dir, "backups")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"full-backup-{stamp}.tar.xz")

    with tarfile.open(out_path, "w:xz") as tar:
        for root, dirs, files in os.walk(data_dir):
            dirs[:] = [d for d in dirs if d not in ("backups", "__pycache__", "cache", ".git")]
            for name in files:
                full_path = os.path.join(root, name)
                if _should_skip(full_path):
                    continue
                if os.path.realpath(full_path) == os.path.realpath(out_path):
                    continue
                arcname = os.path.relpath(full_path, data_dir)
                tar.add(full_path, arcname=arcname)

    # Keep only the last 7 backups on disk (Telegram keeps the rest).
    backups = sorted(f for f in os.listdir(out_dir) if f.startswith("full-backup-"))
    for old in backups[:-7]:
        try:
            os.remove(os.path.join(out_dir, old))
        except OSError:
            log.warning("could not prune %s", old)
    log.info("backup created: %s", out_path)
    return out_path
