import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from telegram.constants import ParseMode

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # User info message with Markdown and Emojis
    message_text = (
        f"👤 *First Name:* {user.first_name}\n"
        f"👤 *Last Name:* {user.last_name or 'N/A'}\n"
        f"🆔 *User Name:* @{user.username if user.username else 'N/A'}\n"
        f"🔑 *User ID:* `{user.id}`\n"
        f"🌐 *Language:* {user.language_code or 'N/A'}"
    )

    # Inline buttons layout with emojis
    keyboard = [
        [
            InlineKeyboardButton("👤 User", callback_data="user"),
            InlineKeyboardButton("🌟 Premium", callback_data="premium"),
            InlineKeyboardButton("🤖 Bot", callback_data="bot")
        ],
        [
            InlineKeyboardButton("👥 Group", callback_data="group"),
            InlineKeyboardButton("📢 Channel", callback_data="channel"),
            InlineKeyboardButton("🏛️ Forum", callback_data="forum")
        ],
        [
            InlineKeyboardButton("🏘️ My Group", callback_data="my_group"),
            InlineKeyboardButton("📡 My Channel", callback_data="my_channel"),
            InlineKeyboardButton("🗯️ My Forum", callback_data="my_forum")
        ],
        [
            InlineKeyboardButton("💳 My Account", callback_data="my_account")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

if __name__ == '__main__':
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables.")
    else:
        application = ApplicationBuilder().token(token).build()
        
        start_handler = CommandHandler('start', start)
        application.add_handler(start_handler)
        
        print("Bot is starting...")
        application.run_polling()
