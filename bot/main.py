"""Parham bot entrypoint: seed → db → workers → dashboard → Telegram polling."""
from __future__ import annotations

import asyncio
import logging
import os

from aiohttp import web
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

load_dotenv()

from bot.config import CONFIG  # noqa: E402
from bot.dashboard.app import build_app  # noqa: E402
from bot.db.models import init_db, init_engine  # noqa: E402
from bot.handlers import backup as backup_h  # noqa: E402
from bot.handlers import callbacks, commands, media, messages, onboarding  # noqa: E402
from bot.services import seed as seed_svc  # noqa: E402
from bot.services import workers as workers_svc  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("parham.main")


async def _run_dashboard() -> None:
    app = build_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", CONFIG.port)
    await site.start()
    log.info("dashboard on :%s", CONFIG.port)


async def main() -> None:
    """Boot everything."""
    CONFIG.validate()
    os.makedirs(CONFIG.data_dir, exist_ok=True)

    # 1. Seed the two Hermes backups on first run (newer overlay wins).
    seed_svc.seed_if_needed(CONFIG.data_dir, os.path.join(os.getcwd(), "seed"))

    # 2. Database (always inside DATA_DIR — nothing on the phone).
    init_engine(CONFIG.db_path)
    await init_db()

    # 3. Telegram application.
    app = Application.builder().token(CONFIG.bot_token).build()
    app.add_handler(onboarding.onboarding_handler())
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
    app.add_handler(CallbackQueryHandler(callbacks.on_feedback, pattern=r"^fb:"))
    app.add_handler(MessageHandler(filters.VOICE, media.handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, media.handle_photo))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, messages.handle_message)
    )

    # 4. Workers (dollar hourly/midnight, memory-backup, pairing-watch).
    workers_svc.start_workers(app)

    # 5. Dashboard (Parham panel on $PORT).
    await _run_dashboard()

    # 6. Telegram (polling — zero config, works on Railway).
    log.info("starting polling")
    await app.initialize()
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
