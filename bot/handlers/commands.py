"""Bot commands: help/settings/clear/memory/forget/mode/reconfig/lang."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.services.memory import (
    clear_facts,
    clear_history,
    get_facts,
    get_or_create_user,
    save_user,
)

MODES: list[tuple[str, str]] = [
    ("🎯 دقیق", "precise"),
    ("🎨 خلاق", "creative"),
    ("⚡ کوتاه", "short"),
    ("💬 معمولی", "normal"),
]


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the command list."""
    await update.message.reply_text(
        "راهنما 😎\n"
        "/start — شروع و معرفی\n"
        "/help — همین لیست\n"
        "/settings — تنظیمات\n"
        "/clear — پاک کردن تاریخچه\n"
        "/memory — چی ازت یاد گرفتم\n"
        "/forget — فراموش کردن همه‌چیز\n"
        "/mode — حالت جواب (دقیق/خلاق/کوتاه/معمولی)\n"
        "/reconfig — تغییر اسم و شخصیت و شهر و علایق\n"
        "/lang — زبان جواب\n"
        "/backup — (فقط مالک) بکاپ کامل\n"
        "بقیه‌شو فقط حرف بزن، خودم می‌فهمم 😉"
    )


async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current settings."""
    user = await get_or_create_user(update.effective_user.id)
    await update.message.reply_text(
        f"تنظیماتت:\n"
        f"اسم: {user.real_name or '—'}\n"
        f"اسم من: {user.bot_name}\n"
        f"شهر: {user.city or '—'}\n"
        f"علایق: {user.interests or '—'}\n"
        f"حالت: {user.mode}\n"
        f"زبان: {user.lang}\n"
        f"با /reconfig عوضشون کن."
    )


async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear chat history."""
    await clear_history(update.effective_user.id)
    await update.message.reply_text("تاریخچه پاک شد 🧹")


async def memory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show learned facts."""
    facts = await get_facts(update.effective_user.id)
    if not facts:
        await update.message.reply_text("هنوز چیزی ازت یاد نگرفتم 🤷")
        return
    lines = "\n".join(f"- {k}: {v}" for k, v in facts.items())
    await update.message.reply_text(f"اینا رو ازت یاد گرفتم:\n{lines}")


async def forget_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forget all facts + history."""
    await clear_facts(update.effective_user.id)
    await clear_history(update.effective_user.id)
    await update.message.reply_text("همه‌چی رو فراموش کردم 🫥")


async def mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pick answer mode with buttons."""
    keyboard = [[InlineKeyboardButton(label, callback_data=f"mode:{key}")] for label, key in MODES]
    await update.message.reply_text(
        "حالت جواب رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Store the picked mode."""
    query = update.callback_query
    await query.answer()
    user = await get_or_create_user(update.effective_user.id)
    user.mode = query.data.split(":", 1)[1]
    await save_user(user)
    await query.message.reply_text("حالت عوض شد ✅")


async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set reply language (default auto-detect)."""
    args = context.args
    user = await get_or_create_user(update.effective_user.id)
    if not args:
        user.lang = "auto"
        await save_user(user)
        await update.message.reply_text("زبان برگشت روی خودکار (به زبان خودت جواب می‌دم) ✅")
        return
    user.lang = args[0][:16]
    await save_user(user)
    await update.message.reply_text(f"زبان شد: {user.lang} ✅")
