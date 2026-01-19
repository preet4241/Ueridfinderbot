from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonRequestUsers, KeyboardButtonRequestChat, ChatAdministratorRights
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

import os
import logging
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

    # Keyboard buttons to request users/chats
    # user_administrator_rights requires a ChatAdministratorRights object
    admin_rights = ChatAdministratorRights(
        is_anonymous=False,
        can_manage_chat=True,
        can_delete_messages=False,
        can_manage_video_chats=False,
        can_restrict_members=False,
        can_promote_members=False,
        can_change_info=False,
        can_invite_users=False,
        can_post_messages=False,
        can_edit_messages=False,
        can_pin_messages=False,
        can_post_stories=False,
        can_edit_stories=False,
        can_delete_stories=False,
        can_manage_topics=False
    )

    reply_keyboard = [
        [
            KeyboardButton("👤 User", request_users=KeyboardButtonRequestUsers(request_id=1, user_is_bot=False, max_quantity=1)),
            KeyboardButton("🌟 Premium", request_users=KeyboardButtonRequestUsers(request_id=2, user_is_premium=True, max_quantity=1)),
            KeyboardButton("🤖 Bot", request_users=KeyboardButtonRequestUsers(request_id=3, user_is_bot=True, max_quantity=1))
        ],
        [
            KeyboardButton("👥 Group", request_chat=KeyboardButtonRequestChat(request_id=4, chat_is_channel=False)),
            KeyboardButton("📢 Channel", request_chat=KeyboardButtonRequestChat(request_id=5, chat_is_channel=True)),
            KeyboardButton("🏛️ Forum", request_chat=KeyboardButtonRequestChat(request_id=6, chat_is_channel=False, chat_is_forum=True))
        ],
        [
            KeyboardButton("🏘️ My Group", request_chat=KeyboardButtonRequestChat(request_id=7, chat_is_channel=False, user_administrator_rights=admin_rights)),
            KeyboardButton("📡 My Channel", request_chat=KeyboardButtonRequestChat(request_id=8, chat_is_channel=True, user_administrator_rights=admin_rights)),
            KeyboardButton("🗯️ My Forum", request_chat=KeyboardButtonRequestChat(request_id=9, chat_is_channel=False, chat_is_forum=True, user_administrator_rights=admin_rights))
        ],
        [
            KeyboardButton("💳 My Account")
        ]
    ]
    
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    
    await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def handle_users_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users_shared = update.message.users_shared
    for shared_user in users_shared.users:
        user_id = shared_user.user_id
        await update.message.reply_text(
            f"✅ <b>Selected User Info:</b>\n\n"
            f"🔑 <b>User ID:</b> <code>{user_id}</code>\n"
            f"<i>Note: Further details are restricted by Telegram for security.</i>",
            parse_mode=ParseMode.HTML
        )

async def handle_chat_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_shared = update.message.chat_shared
    chat_id = chat_shared.chat_id
    
    await update.message.reply_text(
        f"✅ <b>Selected Chat Info:</b>\n\n"
        f"🔑 <b>Chat ID:</b> <code>{chat_id}</code>",
        parse_mode=ParseMode.HTML
    )

if __name__ == '__main__':
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables.")
    else:
        application = ApplicationBuilder().token(token).build()
        
        application.add_handler(CommandHandler('start', start))
        
        # Handlers for shared users and chats
        application.add_handler(MessageHandler(filters.StatusUpdate.USERS_SHARED, handle_users_shared))
        application.add_handler(MessageHandler(filters.StatusUpdate.CHAT_SHARED, handle_chat_shared))
        
        print("Bot is starting...")
        application.run_polling()
