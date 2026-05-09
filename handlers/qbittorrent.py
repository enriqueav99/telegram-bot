from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules.qbittorrent_client import QBittorrentClient, Torrent

log = logging.getLogger(__name__)

PAGE_SIZE = 8


def _list_keyboard(torrents: list[Torrent], page: int = 0) -> InlineKeyboardMarkup:
    start = page * PAGE_SIZE
    items = torrents[start : start + PAGE_SIZE]
    buttons = []
    for t in items:
        label = f"{t.icon} {t.short_name(35)}"
        if t.state in ("downloading", "forcedDL", "stalledDL", "metaDL"):
            label += f" ({t.progress_str})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"qbt:detail:{t.hash}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"qbt:list:{page - 1}"))
    if start + PAGE_SIZE < len(torrents):
        nav.append(InlineKeyboardButton("➡️", callback_data=f"qbt:list:{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔄 Actualizar", callback_data="qbt:list:0")])
    return InlineKeyboardMarkup(buttons)


def _detail_keyboard(t: Torrent) -> InlineKeyboardMarkup:
    action_row = []
    if t.state in ("pausedDL", "pausedUP"):
        action_row.append(InlineKeyboardButton("▶️ Reanudar", callback_data=f"qbt:resume:{t.hash}"))
    else:
        action_row.append(InlineKeyboardButton("⏸ Pausar", callback_data=f"qbt:pause:{t.hash}"))
    action_row.append(InlineKeyboardButton("🗑 Eliminar", callback_data=f"qbt:del:{t.hash}"))
    return InlineKeyboardMarkup([action_row, [InlineKeyboardButton("⬅️ Lista", callback_data="qbt:list:0")]])


def _detail_text(t: Torrent) -> str:
    lines = [f"{t.icon} *{t.name}*\n"]
    lines.append(f"Progreso: {t.progress_str}  |  Tamaño: {t.size_str}")
    if t.dlspeed > 0:
        lines.append(f"⬇️ {t.dlspeed / 1024:.0f} KB/s  ⬆️ {t.upspeed / 1024:.0f} KB/s")
    lines.append(f"Estado: `{t.state}`")
    return "\n".join(lines)


@require_auth
@require_module("qbittorrent")
async def torrents_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    qbt: QBittorrentClient = context.bot_data["qbt"]
    if not qbt.available:
        await update.message.reply_text("❌ QBITTORRENT_URL no configurada.")
        return
    try:
        torrents = await qbt.torrents()
    except Exception as exc:
        log.exception("qBittorrent list failed")
        await update.message.reply_text(f"❌ Error conectando a qBittorrent: {exc}")
        return
    if not torrents:
        await update.message.reply_text("📭 No hay torrents activos.")
        return
    text = f"🧲 *Torrents* — {len(torrents)} total"
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=_list_keyboard(torrents)
    )


@require_auth
@require_module("qbittorrent")
async def torrent_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    qbt: QBittorrentClient = context.bot_data["qbt"]
    if not qbt.available:
        await update.message.reply_text("❌ QBITTORRENT_URL no configurada.")
        return
    if not context.args:
        await update.message.reply_text("Uso: `/torrent <magnet_o_url>`", parse_mode="Markdown")
        return
    url = context.args[0]
    try:
        ok = await qbt.add(url)
        if ok:
            await update.message.reply_text("✅ Torrent añadido")
        else:
            await update.message.reply_text("❌ No se pudo añadir el torrent")
    except Exception as exc:
        log.exception("qBittorrent add failed")
        await update.message.reply_text(f"❌ Error: {exc}")


async def qbt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config = context.bot_data["config"]
    features = context.bot_data["features"]
    user = update.effective_user

    if config.allowed_users and user.id not in config.allowed_users:
        await query.answer("⛔ Sin permiso", show_alert=True)
        return
    if not features.is_enabled("qbittorrent"):
        await query.answer("Módulo qBittorrent desactivado", show_alert=True)
        return

    qbt: QBittorrentClient = context.bot_data["qbt"]
    parts = query.data.split(":", 2)
    action = parts[1]

    try:
        if action == "list":
            page = int(parts[2]) if len(parts) > 2 else 0
            torrents = await qbt.torrents()
            if not torrents:
                await query.edit_message_text("📭 No hay torrents activos.")
                return
            await query.edit_message_text(
                f"🧲 *Torrents* — {len(torrents)} total",
                parse_mode="Markdown",
                reply_markup=_list_keyboard(torrents, page),
            )

        elif action == "detail":
            hash_ = parts[2]
            torrents = await qbt.torrents()
            t = next((t for t in torrents if t.hash == hash_), None)
            if not t:
                await query.answer("Torrent no encontrado", show_alert=True)
                return
            await query.edit_message_text(
                _detail_text(t), parse_mode="Markdown", reply_markup=_detail_keyboard(t)
            )

        elif action == "pause":
            await qbt.pause(parts[2])
            await query.answer("⏸ Pausado")
            torrents = await qbt.torrents()
            t = next((t for t in torrents if t.hash == parts[2]), None)
            if t:
                await query.edit_message_text(
                    _detail_text(t), parse_mode="Markdown", reply_markup=_detail_keyboard(t)
                )

        elif action == "resume":
            await qbt.resume(parts[2])
            await query.answer("▶️ Reanudado")
            torrents = await qbt.torrents()
            t = next((t for t in torrents if t.hash == parts[2]), None)
            if t:
                await query.edit_message_text(
                    _detail_text(t), parse_mode="Markdown", reply_markup=_detail_keyboard(t)
                )

        elif action == "del":
            await qbt.delete(parts[2])
            await query.answer("🗑 Eliminado")
            torrents = await qbt.torrents()
            if not torrents:
                await query.edit_message_text("📭 No hay torrents activos.")
            else:
                await query.edit_message_text(
                    f"🧲 *Torrents* — {len(torrents)} total",
                    parse_mode="Markdown",
                    reply_markup=_list_keyboard(torrents),
                )

    except Exception as exc:
        log.exception("qBittorrent callback failed")
        await query.answer(f"Error: {exc}", show_alert=True)
