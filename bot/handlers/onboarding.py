"""AI-driven onboarding: /start and /reconfig hand the conversation to the
agent — no hardcoded question steps. The agent asks (name → bot name →
city → interests → personality) conversationally and stores answers via
[MEMORY: key=value] tags (see bot.ai.prompts).
"""
from __future__ import annotations

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from bot.handlers.messages import answer_for, send_reply
from bot.services.memory import clear_facts, get_or_create_user, save_user


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start (or resume) the conversation through the agent."""
    user_id = update.effective_user.id
    db_user = await get_or_create_user(user_id, update.effective_user.username or "")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    if db_user.onboarded:
        trigger = "[SYSTEM: کاربر /start زد و قبلاً معرفی شده. صمیمی خوش‌آمد بگو و بپرس چی کار داره.]"
    else:
        trigger = "[SYSTEM: کاربر /start زد و هنوز معرفی نشده. مکالمه آشنایی را قدم‌به‌قدم شروع کن.]"
    reply = await answer_for(user_id, trigger)
    await send_reply(update.message, user_id, reply)


async def reconfig_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset profile and let the agent re-onboard conversationally."""
    user_id = update.effective_user.id
    db_user = await get_or_create_user(user_id)
    db_user.real_name = ""
    db_user.bot_name = ""
    db_user.personality = ""
    db_user.city = ""
    db_user.interests = ""
    db_user.onboarded = False
    await save_user(db_user)
    await clear_facts(user_id)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    trigger = "[SYSTEM: کاربر خواست از اول شروع کند (/reconfig). پروفایلش پاک شد. مکالمه آشنایی را از اول شروع کن.]"
    reply = await answer_for(user_id, trigger)
    await send_reply(update.message, user_id, reply)
