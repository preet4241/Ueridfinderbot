from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonRequestUsers, KeyboardButtonRequestChat, ChatAdministratorRights, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, InlineQueryHandler
from telegram.constants import ParseMode

import os
import logging
import html
import uuid

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await show_user_info(update, user, "Your Profile Info")

    # Keyboard buttons to request users/chats
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
    
    await update.message.reply_text("Choose an option from the menu below:", reply_markup=reply_markup)

async def handle_users_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users_shared = update.message.users_shared
    for shared_user in users_shared.users:
        user_id = shared_user.user_id
        try:
            # Try to fetch full user info using get_chat
            user_chat = await context.bot.get_chat(user_id)
            
            first_name = html.escape(user_chat.first_name or "N/A")
            last_name = html.escape(user_chat.last_name or "N/A")
            username = html.escape(user_chat.username) if user_chat.username else "N/A"
            bio = html.escape(user_chat.bio or "N/A")
            # In python-telegram-bot, the Chat object (returned by get_chat) 
            # might not have a direct is_premium field like the User object.
            # We check for it safely.
            is_premium = "Yes 🌟" if getattr(user_chat, 'is_premium', False) else "No"
            
            message_text = (
                f"✅ <b>User Info Found:</b>\n\n"
                f"👤 <b>First Name:</b> {first_name}\n"
                f"👤 <b>Last Name:</b> {last_name}\n"
                f"🆔 <b>User Name:</b> @{username}\n"
                f"🔑 <b>User ID:</b> <code>{user_id}</code>\n"
                f"🌟 <b>Premium:</b> {is_premium}\n"
                f"📝 <b>Bio:</b> {bio}"
            )
            await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            # Fallback if get_chat fails (usually due to privacy or bot not having seen the user)
            await update.message.reply_text(
                f"✅ <b>Selected User ID:</b> <code>{user_id}</code>\n\n"
                f"💡 <i>I could only get the ID. To see full details, the user must have interacted with me before or you can forward their message!</i>",
                parse_mode=ParseMode.HTML
            )

async def handle_chat_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_shared = update.message.chat_shared
    chat_id = chat_shared.chat_id
    try:
        # Fetch full chat info
        chat = await context.bot.get_chat(chat_id)
        title = html.escape(chat.title or "N/A")
        username = html.escape(chat.username) if chat.username else "N/A"
        description = html.escape(chat.description or "N/A")
        members_count = await chat.get_member_count()
        
        message_text = (
            f"✅ <b>Chat Info Found:</b>\n\n"
            f"🏷️ <b>Title:</b> {title}\n"
            f"🆔 <b>User Name:</b> @{username}\n"
            f"🔑 <b>Chat ID:</b> <code>{chat_id}</code>\n"
            f"👥 <b>Members:</b> {members_count}\n"
            f"📝 <b>Description:</b> {description}"
        )
        await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)
    except Exception:
        await update.message.reply_text(
            f"✅ <b>Selected Chat ID:</b> <code>{chat_id}</code>",
            parse_mode=ParseMode.HTML
        )

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "💳 My Account":
        user = update.effective_user
        await show_user_info(update, user, "Your Account Info")
    elif update.message.forward_origin:
        origin = update.message.forward_origin
        if hasattr(origin, 'sender_user'):
            await show_user_info(update, origin.sender_user, "Forwarded User Info")
        elif hasattr(origin, 'chat'):
            await update.message.reply_text(
                f"📢 <b>Forwarded Chat Info:</b>\n\n"
                f"🏷️ <b>Title:</b> {html.escape(origin.chat.title)}\n"
                f"🔑 <b>Chat ID:</b> <code>{origin.chat.id}</code>",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text("❌ Could not get info from this forward (Privacy settings).")

async def show_user_info(update, user, title):
    first_name = html.escape(user.first_name)
    last_name = html.escape(user.last_name or 'N/A')
    username = html.escape(user.username) if user.username else 'N/A'
    user_id = user.id
    language = html.escape(user.language_code or 'N/A')
    is_premium = "Yes 🌟" if user.is_premium else "No"

    message_text = (
        f"👤 <b>{title}:</b>\n\n"
        f"👤 <b>First Name:</b> {first_name}\n"
        f"👤 <b>Last Name:</b> {last_name}\n"
        f"🆔 <b>User Name:</b> @{username}\n"
        f"🔑 <b>User ID:</b> <code>{user_id}</code>\n"
        f"🌐 <b>Language:</b> {language}\n"
        f"🌟 <b>Premium:</b> {is_premium}"
    )
    await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    user = update.inline_query.from_user
    
    # Show user's own info as an inline result
    first_name = html.escape(user.first_name)
    last_name = html.escape(user.last_name or 'N/A')
    username = html.escape(user.username) if user.username else 'N/A'
    user_id = user.id
    language = html.escape(user.language_code or 'N/A')
    is_premium = "Yes 🌟" if user.is_premium else "No"

    content = (
        f"👤 <b>User Info:</b>\n\n"
        f"👤 <b>First Name:</b> {first_name}\n"
        f"👤 <b>Last Name:</b> {last_name}\n"
        f"🆔 <b>User Name:</b> @{username}\n"
        f"🔑 <b>User ID:</b> <code>{user_id}</code>\n"
        f"🌐 <b>Language:</b> {language}\n"
        f"🌟 <b>Premium:</b> {is_premium}"
    )

    results = [
        InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="My Info",
            description="Send your profile info",
            input_message_content=InputTextMessageContent(content, parse_mode=ParseMode.HTML)
        )
    ]
    await update.inline_query.answer(results, cache_time=1)

if __name__ == '__main__':
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables.")
    else:
        application = ApplicationBuilder().token(token).build()
        
        application.add_handler(CommandHandler('start', start))
        application.add_handler(MessageHandler(filters.StatusUpdate.USERS_SHARED, handle_users_shared))
        application.add_handler(MessageHandler(filters.StatusUpdate.CHAT_SHARED, handle_chat_shared))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
        application.add_handler(InlineQueryHandler(inline_query))
        
        print("Bot is starting...")
        application.run_polling()
