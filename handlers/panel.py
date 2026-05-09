from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import FEATURE_LABELS
from handlers.auth import require_auth

log = logging.getLogger(__name__)


def _build_keyboard(features: dict[str, bool]) -> InlineKeyboardMarkup:
    buttons = []
    for key, enabled in features.items():
        label = FEATURE_LABELS.get(key, key)
        icon = "✅" if enabled else "❌"
        buttons.append([InlineKeyboardButton(f"{icon} {label}", callback_data=f"panel:toggle:{key}")])
    buttons.append([InlineKeyboardButton("🔄 Actualizar", callback_data="panel:refresh")])
    return InlineKeyboardMarkup(buttons)


def _panel_text(features: dict[str, bool]) -> str:
    lines = ["🤖 *Panel de Control del Homelab*\n", "Activa o desactiva los módulos:\n"]
    for key, enabled in features.items():
        label = FEATURE_LABELS.get(key, key)
        state = "activado" if enabled else "desactivado"
        lines.append(f"  {'✅' if enabled else '❌'} {label} — _{state}_")
    return "\n".join(lines)


@require_auth
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    features = context.bot_data["features"]
    flags = features.all()
    await update.message.reply_text(
        _panel_text(flags),
        parse_mode="Markdown",
        reply_markup=_build_keyboard(flags),
    )


async def panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config = context.bot_data["config"]
    user = update.effective_user
    if config.allowed_users and user.id not in config.allowed_users:
        await query.answer("⛔ Sin permiso", show_alert=True)
        return

    features = context.bot_data["features"]
    data = query.data

    if data == "panel:refresh":
        flags = features.all()
        await query.edit_message_text(
            _panel_text(flags),
            parse_mode="Markdown",
            reply_markup=_build_keyboard(flags),
        )
        return

    if data.startswith("panel:toggle:"):
        key = data.split(":", 2)[2]
        try:
            new_state = features.toggle(key)
        except ValueError:
            await query.answer("Feature desconocida", show_alert=True)
            return
        label = FEATURE_LABELS.get(key, key)
        state_str = "activado" if new_state else "desactivado"
        log.info("User %s toggled %s → %s", user.id, key, state_str)
        await query.answer(f"{label} {state_str}")
        flags = features.all()
        await query.edit_message_text(
            _panel_text(flags),
            parse_mode="Markdown",
            reply_markup=_build_keyboard(flags),
        )
