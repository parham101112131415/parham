"""Parham bot entrypoint: seed → db → workers → Telegram polling.

The web dashboard on $PORT is the REAL Hermes dashboard
(`hermes dashboard` from start.sh) — this process only runs Telegram.
"""
from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram import BotCommand, BotCommandScopeChat, BotCommandScopeDefault, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

load_dotenv()

from bot.config import CONFIG  # noqa: E402
from bot.db.models import init_db, init_engine  # noqa: E402
from bot.handlers import backup as backup_h  # noqa: E402
from bot.handlers import callbacks, commands, diag, media, messages, onboarding  # noqa: E402
from bot.services import seed as seed_svc  # noqa: E402
from bot.services import workers as workers_svc  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("parham.main")


# Bot command menu — set automatically on every boot, exactly like a
# Hermes gateway deploy (menu button next to the chat input).
PUBLIC_COMMANDS = [
    BotCommand("start", "شروع و معرفی"),
    BotCommand("help", "راهنما"),
    BotCommand("settings", "تنظیمات"),
    BotCommand("clear", "پاک کردن تاریخچه"),
    BotCommand("memory", "چی ازت یاد گرفتم"),
    BotCommand("forget", "فراموش کردن همه‌چیز"),
    BotCommand("mode", "حالت جواب"),
    BotCommand("reconfig", "شروع از اول"),
    BotCommand("lang", "زبان جواب"),
]

OWNER_COMMANDS = PUBLIC_COMMANDS + [
    BotCommand("backup", "بکاپ کامل (مالک)"),
    BotCommand("restore", "ریستور از فایل (مالک)"),
    BotCommand("status", "وضعیت مغز بات (مالک)"),
]


async def _set_menus(app: Application) -> None:
    """Publish the command menus (public + owner scope)."""
    try:
        await app.bot.set_my_commands(PUBLIC_COMMANDS, scope=BotCommandScopeDefault())
        if CONFIG.owner_id:
            await app.bot.set_my_commands(
                OWNER_COMMANDS, scope=BotCommandScopeChat(chat_id=CONFIG.owner_id)
            )
        log.info("command menus published")
    except Exception:  # noqa: BLE001
        log.exception("failed to publish command menus")


async def main() -> None:
    """Boot everything."""
    CONFIG.validate()
    os.makedirs(CONFIG.data_dir, exist_ok=True)

    # 1. Seed the two Hermes backups on first run (newer overlay wins).
    seed_svc.seed_if_needed(CONFIG.data_dir, os.path.join(os.getcwd(), "seed"))

    # 2. Database (always inside DATA_DIR — nothing on the phone).
    init_engine(CONFIG.db_path)
    await init_db()

    # 3. Telegram application (onboarding is AI-driven — no step handlers).
    app = Application.builder().token(CONFIG.bot_token).build()
    app.add_handler(CommandHandler("start", onboarding.start_cmd))
    app.add_handler(CommandHandler("reconfig", onboarding.reconfig_cmd))
    app.add_handler(CommandHandler("help", commands.help_cmd))
    app.add_handler(CommandHandler("settings", commands.settings_cmd))
    app.add_handler(CommandHandler("clear", commands.clear_cmd))
    app.add_handler(CommandHandler("memory", commands.memory_cmd))
    app.add_handler(CommandHandler("forget", commands.forget_cmd))
    app.add_handler(CommandHandler("mode", commands.mode_cmd))
    app.add_handler(CallbackQueryHandler(commands.mode_callback, pattern=r"^mode:"))
    app.add_handler(CommandHandler("lang", commands.lang_cmd))
    app.add_handler(CommandHandler("backup", backup_h.backup_cmd))
    app.add_handler(CommandHandler("restore", backup_h.restore_cmd))
    app.add_handler(CommandHandler("status", diag.status_cmd))
    app.add_handler(CallbackQueryHandler(callbacks.on_feedback, pattern=r"^fb:"))
    app.add_handler(MessageHandler(filters.VOICE, media.handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, media.handle_photo))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, messages.handle_message)
    )

    # 4. Workers (dollar hourly/midnight, memory-backup, pairing-watch).
    workers_svc.start_workers(app)

    # 5. Telegram (polling — zero config, works on Railway).
    #    NOTE: $PORT belongs to the real Hermes dashboard (see start.sh).
    log.info("starting polling")
    await app.initialize()
    await _set_menus(app)
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
