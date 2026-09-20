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
    save_user,
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


# User-profile keys the agent stores via [MEMORY: key=value].
PROFILE_KEYS = {"real_name", "bot_name", "city", "interests", "personality"}


async def answer_for(user_id: int, text: str) -> str:
    """Run the agent pipeline for a user message and return the clean reply."""
    is_owner = CONFIG.is_owner(user_id)
    db_user = await get_or_create_user(user_id)
    facts = await get_facts(user_id)
    system = build_system_prompt(db_user, facts, is_owner=is_owner)
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
            allow_edit=is_owner,
        )

    clean, new_facts = extract_memory_tags(reply)
    profile_changed = False
    for key, value in new_facts.items():
        if key in PROFILE_KEYS:
            setattr(db_user, key, value[:500])
            profile_changed = True
        else:
            await save_fact(user_id, key, value)
    if profile_changed:
        await save_user(db_user)
    if not db_user.onboarded and all(
        [db_user.real_name, db_user.bot_name, db_user.city, db_user.interests]
    ):
        db_user.onboarded = True
        await save_user(db_user)
    await add_message(user_id, "user", text, CONFIG.history_limit)
    await add_message(user_id, "assistant", clean, CONFIG.history_limit)
    return clean


async def send_reply(message, user_id: int, reply: str) -> None:
    """Send a reply chunked (spec) with the italic follow-up + buttons."""
    _last_replies[user_id] = reply
    chunks = split_chunks(reply, CONFIG.chunk_size)
    follow_up = f"_{random.choice(FOLLOW_UPS)}_"
    for i, chunk in enumerate(chunks):
        await asyncio.sleep(random.uniform(0.4, 0.7))
        last = i == len(chunks) - 1
        markup = feedback_keyboard() if last else None
        body = f"{chunk}\n\n{follow_up}" if last else chunk
        try:
            await message.reply_text(
                body, parse_mode=ParseMode.MARKDOWN, reply_markup=markup
            )
        except Exception:  # noqa: BLE001
            log.warning("markdown send failed, retrying plain")
            await message.reply_text(chunk, reply_markup=markup)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a plain text message."""
    if not update.message or not update.message.text:
        return
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if not text:
        return

    # No hardcoded gates: the agent itself onboards unknown users.
    await get_or_create_user(user_id)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    try:
        reply = await answer_for(user_id, text)
    except Exception:  # noqa: BLE001
        log.exception("pipeline failed")
        await update.message.reply_text("یه لحظه مشکلی پیش اومد، دوباره امتحان کن")
        return

    await send_reply(update.message, user_id, reply)


def last_reply(user_id: int) -> str:
    """Return the last assistant reply for feedback callbacks."""
    return _last_replies.get(user_id, "")
