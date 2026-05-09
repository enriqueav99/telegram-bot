from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules.github_client import GitHubClient

log = logging.getLogger(__name__)


def _keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔄 Actualizar", callback_data="ci:refresh")]]
    )


def _build_text(runs, repo: str) -> str:
    if not runs:
        return f"🔧 *GitHub Actions* — `{repo}`\n\nNo hay ejecuciones recientes."
    lines = [f"🔧 *GitHub Actions* — `{repo}`\n"]
    for r in runs:
        lines.append(f"{r.emoji} *{r.name}* #{r.run_number}")
        lines.append(f"   `{r.branch}` · {r.event} · {r.age_str}")
        if r.status != "completed":
            lines.append(f"   Estado: _{r.status}_")
        lines.append("")
    return "\n".join(lines).strip()


@require_auth
@require_module("github_actions")
async def ci_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    gh: GitHubClient = context.bot_data["github"]
    if not gh.available:
        await update.message.reply_text(
            "❌ GitHub no configurado.\n\nDefine `GITHUB_TOKEN` y `GITHUB_REPO` en el `.env`.",
            parse_mode="Markdown",
        )
        return
    msg = await update.message.reply_text("⏳ Consultando GitHub Actions...")
    runs = await gh.get_runs()
    if runs is None:
        await msg.edit_text("❌ Error al consultar la API de GitHub.")
        return
    await msg.edit_text(_build_text(runs, gh.repo), parse_mode="Markdown", reply_markup=_keyboard())


async def ci_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config = context.bot_data["config"]
    features = context.bot_data["features"]
    user = update.effective_user

    if config.allowed_users and user.id not in config.allowed_users:
        await query.answer("⛔ Sin permiso", show_alert=True)
        return
    if not features.is_enabled("github_actions"):
        await query.answer("Módulo GitHub Actions desactivado", show_alert=True)
        return

    gh: GitHubClient = context.bot_data["github"]
    runs = await gh.get_runs()
    if runs is None:
        await query.answer("❌ Error consultando GitHub", show_alert=True)
        return
    await query.edit_message_text(
        _build_text(runs, gh.repo), parse_mode="Markdown", reply_markup=_keyboard()
    )
