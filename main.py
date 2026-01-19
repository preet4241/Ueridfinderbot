import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from telegram.constants import ParseMode

import html

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Escape user-provided content to avoid HTML parsing errors
    first_name = html.escape(user.first_name)
    last_name = html.escape(user.last_name or 'N/A')
    username = html.escape(user.username) if user.username else 'N/A'
    user_id = user.id
    language = html.escape(user.language_code or 'N/A')

    # User info message with HTML and Emojis
    message_text = (
        f"👤 <b>First Name:</b> {first_name}\n"
        f"👤 <b>Last Name:</b> {last_name}\n"
        f"🆔 <b>User Name:</b> @{username}\n"
        f"🔑 <b>User ID:</b> <code>{user_id}</code>\n"
        f"🌐 <b>Language:</b> {language}"
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
    
    await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

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
