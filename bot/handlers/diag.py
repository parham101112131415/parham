"""Owner-only /status diagnostic: is the opencode brain reachable?"""
from __future__ import annotations

import os
import shutil
import socket
import urllib.parse

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import CONFIG


def _serve_reachable(url: str) -> str:
    try:
        parts = urllib.parse.urlparse(url)
        host = parts.hostname or "127.0.0.1"
        port = parts.port or 80
        with socket.create_connection((host, port), timeout=5):
            return "ok"
    except Exception as exc:  # noqa: BLE001
        return f"FAIL: {exc}"


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show brain + runtime diagnostics (owner only)."""
    if not CONFIG.is_owner(update.effective_user.id):
        await update.message.reply_text("این دستور فقط برای مالک رباته 🔒")
        return

    binary = shutil.which("opencode") or "NOT FOUND"
    serve = _serve_reachable(CONFIG.opencode_serve_url)
    err_path = os.path.join(CONFIG.data_dir, "opencode_last_error.log")
    last_err = "—"
    if os.path.exists(err_path):
        with open(err_path, errors="ignore") as fh:
            last_err = fh.read()[-800:] or "—"
    db_path = CONFIG.db_path
    db_size = f"{os.path.getsize(db_path) / 1024:.0f}KB" if os.path.exists(db_path) else "missing"
    seed_marker = "yes" if os.path.exists(os.path.join(CONFIG.data_dir, ".seeded")) else "no"

    await update.message.reply_text(
        "🔧 وضعیت:\n"
        f"backend: {CONFIG.ai_backend}\n"
        f"model: {CONFIG.opencode_model}\n"
        f"opencode: {binary}\n"
        f"serve ({CONFIG.opencode_serve_url}): {serve}\n"
        f"db: {db_size} | seed: {seed_marker}\n"
        f"آخرین خطا:\n{last_err}"
    )
