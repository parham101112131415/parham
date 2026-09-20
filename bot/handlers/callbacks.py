"""Feedback button callbacks: 👍 👎 🔄 💬."""
from __future__ import annotations

import logging

from sqlalchemy import insert, select
from telegram import Update
from telegram.ext import ContextTypes

from bot.db.models import Feedback, session_factory
from bot.handlers.messages import answer_for, feedback_keyboard, last_reply
from bot.services.chunker import split_chunks
from bot.config import CONFIG

log = logging.getLogger("parham.callbacks")


async def _record(user_id: int, kind: str) -> None:
    factory = session_factory()
    async with factory() as session:
        session.add(Feedback(telegram_id=user_id, kind=kind))
        await session.commit()


async def on_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle feedback inline buttons."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    action = query.data.split(":", 1)[1]

    if action == "like":
        await _record(user_id, "like")
        await query.message.reply_text("🔥 دمت گرم!")
    elif action == "dislike":
        await _record(user_id, "dislike")
        await query.message.reply_text("باشه، دفعه بعد بهترش می‌کنم. بگو چی بد بود؟")
    elif action == "regen":
        prev = last_reply(user_id)
        prompt = f"این جواب قبلیت بود:\n{prev}\nیه جواب جدید و متفاوت بده." if prev else "یه جواب جدید بده."
        await query.message.chat.send_action("typing")
        reply = await answer_for(user_id, prompt)
        for chunk in split_chunks(reply, CONFIG.chunk_size):
            await query.message.reply_text(chunk, reply_markup=feedback_keyboard())
    elif action == "more":
        prev = last_reply(user_id)
        prompt = f"این جواب قبلیت بود:\n{prev}\nادامه‌ش بده و بیشتر توضیح بده." if prev else "بیشتر توضیح بده."
        await query.message.chat.send_action("typing")
        reply = await answer_for(user_id, prompt)
        for chunk in split_chunks(reply, CONFIG.chunk_size):
            await query.message.reply_text(chunk, reply_markup=feedback_keyboard())
