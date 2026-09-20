"""Onboarding flow: name → personality → city → interests (spec)."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.ai.prompts import PERSONALITY_BUTTONS
from bot.services.memory import get_or_create_user, save_user

NAME, PERSONALITY, CITY, INTERESTS = range(4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: ask for the user's name."""
    user = update.effective_user
    await get_or_create_user(user.id, user.username or "")
    await update.message.reply_text("سلام! من پارهمم 😎\nاسمت چیه؟")
    return NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store name, ask for personality."""
    db_user = await get_or_create_user(update.effective_user.id)
    db_user.real_name = (update.message.text or "").strip()[:128]
    await save_user(db_user)
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"personality:{key}")]
        for label, key in PERSONALITY_BUTTONS
    ]
    keyboard.append([InlineKeyboardButton("✍️ خودم توصیف می‌کنم", callback_data="personality:custom")])
    await update.message.reply_text(
        f"خوشبختم {db_user.real_name}! می‌خوای چجوری باشم؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return PERSONALITY


async def ask_personality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store personality (button or custom text), ask for city/timezone."""
    query = update.callback_query
    await query.answer()
    choice = query.data.split(":", 1)[1]
    if choice == "custom":
        await query.message.reply_text("بگو دقیقاً چه شخصیتی داشته باشم؟ (مثلاً: مثل یه رفیق باش که کم حرف می‌زنه)")
        return PERSONALITY
    db_user = await get_or_create_user(update.effective_user.id)
    db_user.personality = choice
    await save_user(db_user)
    await query.message.reply_text("کجایی؟ (شهرت — برای ساعت و زمان‌بندی)")
    return CITY


async def ask_personality_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store a free-text personality, or the city if personality is already set."""
    db_user = await get_or_create_user(update.effective_user.id)
    if context.user_data.pop("awaiting_personality", None) or not db_user.personality:
        db_user.personality = (update.message.text or "").strip()[:500]
        await save_user(db_user)
        await update.message.reply_text("کجایی؟ (شهرت — برای ساعت و زمان‌بندی)")
        return CITY
    return await ask_city(update, context)


async def ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store city, ask for interests."""
    db_user = await get_or_create_user(update.effective_user.id)
    db_user.city = (update.message.text or "").strip()[:128]
    await save_user(db_user)
    await update.message.reply_text("به چه چیزایی علاقه داری؟ (با کاما جدا کن)")
    return INTERESTS


async def finish_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store interests, mark onboarded."""
    db_user = await get_or_create_user(update.effective_user.id)
    db_user.interests = (update.message.text or "").strip()[:500]
    db_user.onboarded = True
    await save_user(db_user)
    await update.message.reply_text(
        "تمومه! از این به بعد من دقیقاً همونم که گفتی 😎\n"
        "با /reconfig می‌تونی هر وقت خواستی عوضم کنی. بگو چی تو ذهنته؟"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel onboarding."""
    await update.message.reply_text("باشه، بعداً با /start ادامه می‌دیم.")
    return ConversationHandler.END


async def reconfig_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reset profile and restart onboarding."""
    db_user = await get_or_create_user(update.effective_user.id)
    db_user.real_name = ""
    db_user.personality = ""
    db_user.city = ""
    db_user.interests = ""
    db_user.onboarded = False
    await save_user(db_user)
    context.user_data.clear()
    await update.message.reply_text("باشه از اول 😎 اسمت چیه؟")
    return NAME


def onboarding_handler() -> ConversationHandler:
    """Build the onboarding ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("reconfig", reconfig_entry),
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            PERSONALITY: [
                CallbackQueryHandler(ask_personality, pattern=r"^personality:(?!custom$)"),
                CallbackQueryHandler(
                    lambda u, c: _prompt_custom(u, c), pattern=r"^personality:custom$"
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_personality_custom),
            ],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_city)],
            INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_onboarding)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="onboarding",
        persistent=False,
    )


async def _prompt_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["awaiting_personality"] = True
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("بگو دقیقاً چه شخصیتی داشته باشم؟")
    return PERSONALITY
