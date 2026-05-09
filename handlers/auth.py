from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING, Any, Callable, Coroutine

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

log = logging.getLogger(__name__)


def require_auth(func: Callable[..., Coroutine[Any, Any, None]]):
    """Rechaza el comando si el usuario no está en ALLOWED_USERS."""

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        config = context.bot_data["config"]
        user = update.effective_user
        if config.allowed_users and user.id not in config.allowed_users:
            log.warning("Acceso denegado a user_id=%s username=%s", user.id, user.username)
            await update.effective_message.reply_text("⛔ No tienes permiso para usar este bot.")
            return
        return await func(update, context, *args, **kwargs)

    return wrapper


def require_module(module: str):
    """Rechaza el comando si el módulo está desactivado en el panel."""

    def decorator(func: Callable[..., Coroutine[Any, Any, None]]):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            features = context.bot_data["features"]
            if not features.is_enabled(module):
                await update.effective_message.reply_text(
                    f"❌ El módulo *{module}* está desactivado\\.\n"
                    f"Actívalo desde /panel",
                    parse_mode="MarkdownV2",
                )
                return
            return await func(update, context, *args, **kwargs)

        return wrapper

    return decorator
