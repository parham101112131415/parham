"""Owner-only /backup and /restore (reply to a backup file)."""
from __future__ import annotations

import logging
import os
import tarfile

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import CONFIG
from bot.services.backup import create_backup

log = logging.getLogger("parham.backup_cmd")


def _owner_only(update: Update) -> bool:
    return CONFIG.is_owner(update.effective_user.id)


async def backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a full backup and send it to the owner."""
    if not _owner_only(update):
        await update.message.reply_text("این دستور فقط برای مالک رباته 🔒")
        return
    await update.message.reply_text("دارم بکاپ کامل می‌گیرم... ⏳")
    try:
        path = await context.application.run_in_executor(None, create_backup, CONFIG.data_dir)
    except Exception:  # noqa: BLE001
        log.exception("backup failed")
        await update.message.reply_text("بکاپ fail شد، لاگ رو چک کن")
        return
    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb > 49:
        await update.message.reply_text(
            f"بکاپ ساخته شد ولی {size_mb:.0f}MBـه و از سقف تلگرام بیشتره.\n"
            f"تو ولوم هست: `{path}`",
            parse_mode="Markdown",
        )
        return
    await update.message.reply_document(document=open(path, "rb"), caption="بکاپ کامل ✅")


async def restore_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Restore from a backup file sent as reply (/restore in reply to the zip)."""
    if not _owner_only(update):
        await update.message.reply_text("این دستور فقط برای مالک رباته 🔒")
        return
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("فایل بکاپ رو reply کن و /restore بزن.")
        return
    doc = update.message.reply_to_message.document
    if not doc.file_name.endswith((".tar.xz", ".tgz", ".tar.gz")):
        await update.message.reply_text("فرمت بکاپ معتبر نیست.")
        return
    await update.message.reply_text("دارم ریستور می‌کنم... ⏳")
    tmp = os.path.join(CONFIG.data_dir, "_restore_incoming.tar")
    try:
        tg_file = await doc.get_file()
        await tg_file.download_to_drive(tmp)
        with tarfile.open(tmp, "r:*") as tar:
            tar.extractall(CONFIG.data_dir, filter="data")
        marker = os.path.join(CONFIG.data_dir, ".seeded")
        with open(marker, "w") as fh:
            fh.write("restored\n")
    except Exception:  # noqa: BLE001
        log.exception("restore failed")
        await update.message.reply_text("ریستور fail شد.")
        return
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    await update.message.reply_text("ریستور شد ✅ ری‌استارت می‌کنم که همه‌چی برگرده.")
    # Hard restart so opencode serve + workers pick up restored state.
    os._exit(0)  # noqa: SLF001, PTH100
