from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules import wireguard_client
from modules.docker_client import DockerClient

log = logging.getLogger(__name__)


def _keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔄 Actualizar", callback_data="wg:refresh")]]
    )


def _build_text(peers: list[wireguard_client.WgPeer]) -> str:
    if not peers:
        return "🔒 *WireGuard VPN*\n\nNo hay peers configurados."
    connected = sum(1 for p in peers if p.connected)
    lines = [f"🔒 *WireGuard VPN* — {connected}/{len(peers)} conectados\n"]
    for p in peers:
        icon = "🟢" if p.connected else "🔴"
        lines.append(f"{icon} `{p.short_key}`")
        lines.append(f"   IPs: `{p.allowed_ips}`")
        if p.endpoint != "—":
            lines.append(f"   Endpoint: `{p.endpoint}`")
        lines.append(f"   Handshake: {p.handshake_str}")
        lines.append(f"   Tráfico: {p.transfer_str}")
        lines.append("")
    return "\n".join(lines).strip()


@require_auth
@require_module("wireguard")
async def wg_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    docker: DockerClient = context.bot_data["docker"]
    msg = await update.message.reply_text("⏳ Consultando WireGuard...")
    peers = await wireguard_client.get_peers(docker)
    if peers is None:
        await msg.edit_text(
            "❌ No se pudo conectar con el contenedor `wireguard`.", parse_mode="Markdown"
        )
        return
    await msg.edit_text(_build_text(peers), parse_mode="Markdown", reply_markup=_keyboard())


async def wg_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config = context.bot_data["config"]
    features = context.bot_data["features"]
    user = update.effective_user

    if config.allowed_users and user.id not in config.allowed_users:
        await query.answer("⛔ Sin permiso", show_alert=True)
        return
    if not features.is_enabled("wireguard"):
        await query.answer("Módulo WireGuard desactivado", show_alert=True)
        return

    docker: DockerClient = context.bot_data["docker"]
    peers = await wireguard_client.get_peers(docker)
    if peers is None:
        await query.answer("❌ Error conectando con WireGuard", show_alert=True)
        return
    await query.edit_message_text(
        _build_text(peers), parse_mode="Markdown", reply_markup=_keyboard()
    )
