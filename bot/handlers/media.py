"""Media handlers: voice → Whisper → answer, photo → Vision → analysis."""
from __future__ import annotations

import logging
import os
import tempfile

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from bot.config import CONFIG
from bot.handlers.messages import answer_for, feedback_keyboard
from bot.services.chunker import split_chunks
from bot.services.memory import get_or_create_user

log = logging.getLogger("parham.media")


async def _transcribe(ogg_path: str) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=CONFIG.openai_api_key, base_url=CONFIG.openai_base_url)
    try:
        with open(ogg_path, "rb") as fh:
            result = await client.audio.transcriptions.create(model="whisper-1", file=fh)
        return (result.text or "").strip()
    finally:
        await client.close()


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Voice message → transcribe → agent answer."""
    user_id = update.effective_user.id
    db_user = await get_or_create_user(user_id)
    if not db_user.onboarded:
        await update.message.reply_text("اول با /start خودتو معرفی کن 😎")
        return
    if not CONFIG.openai_api_key:
        await update.message.reply_text("ویس فعلاً بدون کلید OpenAI کار نمی‌کنه، متنی بفرست 😎")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        tg_file = await update.message.voice.get_file()
        await tg_file.download_to_drive(tmp_path)
        text = await _transcribe(tmp_path)
    except Exception:  # noqa: BLE001
        log.exception("voice failed")
        await update.message.reply_text("یه لحظه مشکلی پیش اومد، دوباره امتحان کن")
        return
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
    if not text:
        await update.message.reply_text("چیزی از ویست نفهمیدم 🤷")
        return
    reply = await answer_for(user_id, text)
    for chunk in split_chunks(reply, CONFIG.chunk_size):
        await update.message.reply_text(chunk, reply_markup=feedback_keyboard())


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Photo → Vision analysis when API key exists, else forward note to agent."""
    user_id = update.effective_user.id
    db_user = await get_or_create_user(user_id)
    if not db_user.onboarded:
        await update.message.reply_text("اول با /start خودتو معرفی کن 😎")
        return
    caption = (update.message.caption or "").strip()
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    prompt = f"کاربر یک عکس فرستاده{' با این کپشن: ' + caption if caption else ' (بدون کپشن)'}."
    if CONFIG.openai_api_key:
        prompt += " آن را تحلیل کن و بگو چه می‌بینی."
    else:
        prompt += " بگو چه کمکی درباره عکس می‌خواهی (تحلیل کامل عکس نیاز به اتصال Vision دارد)."
    if caption and not CONFIG.openai_api_key:
        prompt = caption
    reply = await answer_for(user_id, prompt)
    for chunk in split_chunks(reply, CONFIG.chunk_size):
        await update.message.reply_text(chunk, reply_markup=feedback_keyboard())
