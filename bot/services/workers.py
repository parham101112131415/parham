"""Background workers (from Hermes jobs-manifest): dollar hourly/midnight,
memory-backup, pairing-watch. Seed scripts under DATA_DIR are executed
no-agent style; missing scripts are skipped gracefully.
"""
from __future__ import annotations

import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from bot.config import CONFIG
from bot.services.backup import create_backup

log = logging.getLogger("parham.workers")


async def _run_script(path: str) -> str:
    """Run a seed python script and return its stdout."""
    proc = await asyncio.create_subprocess_exec(
        "python3", path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        log.warning("%s exited %s: %s", path, proc.returncode, stderr.decode()[-300:])
        return ""
    return stdout.decode("utf-8", "ignore").strip()


def _script(name: str) -> str | None:
    for base in ("scripts", ".hermes/scripts"):
        path = os.path.join(CONFIG.data_dir, base, name)
        if os.path.exists(path):
            return path
    return None


async def dollar_hourly(app: Application) -> None:
    """Hourly dollar snapshot → owner DM (empty output = no price change = silent)."""
    path = _script("fetch_dollar.py")
    if not path:
        return
    out = await _run_script(path)
    if out:
        await app.bot.send_message(chat_id=CONFIG.owner_id, text=out)


async def dollar_midnight(app: Application) -> None:
    """Midnight dollar digest → owner DM."""
    path = _script("dollar_summary.py")
    if not path:
        return
    out = await _run_script(path)
    if out:
        await app.bot.send_message(chat_id=CONFIG.owner_id, text=out)


async def memory_backup_job(app: Application) -> None:
    """Periodic full backup → owner DM."""
    try:
        path = await asyncio.get_running_loop().run_in_executor(
            None, create_backup, CONFIG.data_dir
        )
    except Exception:  # noqa: BLE001
        log.exception("auto backup failed")
        return
    if os.path.getsize(path) > 49 * 1024 * 1024:
        return
    await app.bot.send_document(chat_id=CONFIG.owner_id, document=open(path, "rb"))


async def pairing_watch(app: Application) -> None:
    """Report newly-seen pairing requests (empty output = silent)."""
    path = _script("pairing_watch.py")
    if not path:
        return
    out = await _run_script(path)
    if out:
        await app.bot.send_message(chat_id=CONFIG.owner_id, text=out)


async def _wrap(app: Application, coro, name: str) -> None:
    try:
        await coro(app)
    except Exception:  # noqa: BLE001
        log.exception("worker %s failed", name)


def start_workers(app: Application) -> AsyncIOScheduler:
    """Schedule the 4 workers. Returns the scheduler."""
    scheduler = AsyncIOScheduler(timezone=CONFIG.timezone)
    scheduler.add_job(_wrap, "cron", hour="1-23", args=[app, dollar_hourly, "dollar-hourly"], id="dollar-hourly")
    scheduler.add_job(_wrap, "cron", hour="0", minute="0", args=[app, dollar_midnight, "dollar-midnight"], id="dollar-midnight")
    scheduler.add_job(_wrap, "cron", hour="*/2", minute="35", args=[app, memory_backup_job, "memory-backup"], id="memory-backup")
    scheduler.add_job(_wrap, "cron", minute="*", args=[app, pairing_watch, "pairing-watch"], id="pairing-watch")
    scheduler.start()
    log.info("workers started")
    return scheduler
