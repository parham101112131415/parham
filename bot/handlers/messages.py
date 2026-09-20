"""Main message handler: typing → agent → chunked reply + feedback buttons."""
from __future__ import annotations

import asyncio
import logging
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from bot.ai.bridge import ask_agent
from bot.ai.fallback import ask_openai
from bot.ai.prompts import build_system_prompt
from bot.config import CONFIG
from bot.services.chunker import extract_memory_tags, split_chunks
from bot.services.memory import (
    add_message,
    get_facts,
    get_history,
    get_or_create_user,
    save_fact,
)

log = logging.getLogger("parham.messages")

FOLLOW_UPS = [
    "بگو اگه بخوای عوضش کنم",
    "اگه خواستی ادامه‌ش بدم بگو",
    "نظرت چیه؟ بگو دقیق‌ترش کنم",
]

_last_replies: dict[int, str] = {}


def feedback_keyboard() -> InlineKeyboardMarkup:
    """Inline buttons shown after every reply (spec)."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("👍", callback_data="fb:like"),
                InlineKeyboardButton("👎", callback_data="fb:dislike"),
                InlineKeyboardButton("🔄", callback_data="fb:regen"),
                InlineKeyboardButton("💬", callback_data="fb:more"),
            ]
        ]
    )


async def answer_for(user_id: int, text: str) -> str:
    """Run the agent pipeline for a user message and return the clean reply."""
    db_user = await get_or_create_user(user_id)
    facts = await get_facts(user_id)
    system = build_system_prompt(db_user, facts)
    history = await get_history(user_id, CONFIG.history_limit)

    if CONFIG.ai_backend == "openai" and CONFIG.openai_api_key:
        reply = await ask_openai(
            system,
            history,
            text,
            api_key=CONFIG.openai_api_key,
            base_url=CONFIG.openai_base_url,
            model=CONFIG.openai_model,
        )
    else:
        prompt = f"{system}\n\nتاریخچه:\n" + "\n".join(
            f"{'کاربر' if m['role'] == 'user' else 'دستیار'}: {m['content']}" for m in history
        )
        prompt += f"\n\nپیام جدید کاربر: {text}\nفقط متن جواب را بنویس."
        reply = await ask_agent(
            user_id,
            prompt,
            serve_url=CONFIG.opencode_serve_url,
            model=CONFIG.opencode_model,
        )

    clean, new_facts = extract_memory_tags(reply)
    for key, value in new_facts.items():
        await save_fact(user_id, key, value)
    await add_message(user_id, "user", text, CONFIG.history_limit)
    await add_message(user_id, "assistant", clean, CONFIG.history_limit)
    return clean


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a plain text message."""
    if not update.message or not update.message.text:
        return
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if not text:
        return

    db_user = await get_or_create_user(user_id)
    if not db_user.onboarded:
        await update.message.reply_text("اول با /start خودتو معرفی کن 😎")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    try:
        reply = await answer_for(user_id, text)
    except Exception:  # noqa: BLE001
        log.exception("pipeline failed")
        await update.message.reply_text("یه لحظه مشکلی پیش اومد، دوباره امتحان کن")
        return

    _last_replies[user_id] = reply
    chunks = split_chunks(reply, CONFIG.chunk_size)
    follow_up = f"_{random.choice(FOLLOW_UPS)}_"
    for i, chunk in enumerate(chunks):
        await asyncio.sleep(random.uniform(0.4, 0.7))
        last = i == len(chunks) - 1
        markup = feedback_keyboard() if last else None
        body = f"{chunk}\n\n{follow_up}" if last else chunk
        try:
            await update.message.reply_text(
                body, parse_mode=ParseMode.MARKDOWN, reply_markup=markup
            )
        except Exception:  # noqa: BLE001
            log.warning("markdown send failed, retrying plain")
            await update.message.reply_text(chunk, reply_markup=markup)


def last_reply(user_id: int) -> str:
    """Return the last assistant reply for feedback callbacks."""
    return _last_replies.get(user_id, "")
