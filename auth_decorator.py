from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from auth import is_authenticated

def requires_auth(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = str(update.effective_user.id)
        if not is_authenticated(user_id):
            await update.message.reply_text("🔐 Please login using `/login <pin>` first.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper
