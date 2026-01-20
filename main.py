from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonRequestUsers, KeyboardButtonRequestChat, ChatAdministratorRights, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ParseMode

import os
import logging
import html
import json
import psycopg2
from psycopg2.extras import RealDictCursor

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

OWNER_ID = int(os.environ.get("OWNER_ID", 0))

def get_db_connection():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            language_code TEXT,
            is_premium BOOLEAN,
            is_banned BOOLEAN DEFAULT FALSE,
            ban_reason TEXT,
            unban_at TIMESTAMP,
            bio TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def save_user(user):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, first_name, last_name, username, language_code, is_premium)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            username = EXCLUDED.username,
            language_code = EXCLUDED.language_code,
            is_premium = EXCLUDED.is_premium
    """, (user.id, user.first_name, user.last_name, user.username, user.language_code, user.is_premium))
    conn.commit()
    cur.close()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)
    
    # Common Keyboard
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

    if user.id == OWNER_ID:
        # Owner Dashboard
        inline_keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data="status")],
            [InlineKeyboardButton("👥 Users", callback_data="users_menu"), InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")]
        ]
        inline_markup = InlineKeyboardMarkup(inline_keyboard)
        await update.message.reply_text("👑 <b>Welcome Owner!</b>\nYour Dashboard is ready.", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        await update.message.reply_text("🛠 <b>Admin Panel:</b>", reply_markup=inline_markup, parse_mode=ParseMode.HTML)
    else:
        # Regular User
        # Check if banned
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT is_banned FROM users WHERE user_id = %s", (user.id,))
        res = cur.fetchone()
        if res and res[0]:
            await update.message.reply_text("🚫 You are banned from using this bot.")
            return
        cur.close()
        conn.close()

        await show_user_info(update, user, "Your Profile Info")
        await update.message.reply_text("Choose an option from the menu below:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "status":
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        await query.edit_message_text(f"📊 <b>Bot Status:</b>\nTotal Users: {count}", parse_mode=ParseMode.HTML)
    
    elif query.data == "users_menu":
        keyboard = [
            [InlineKeyboardButton("🚫 Ban User", callback_data="ban_start"), InlineKeyboardButton("✅ Unban User", callback_data="unban")],
            [InlineKeyboardButton("ℹ️ Get Info", callback_data="get_info"), InlineKeyboardButton("📄 Get User List", callback_data="get_list")]
        ]
        await query.edit_message_text("👥 <b>User Management:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif query.data == "ban_start":
        await query.edit_message_text("🚫 <b>Ban User:</b>\nPlease forward a message from the user, or send their User ID or Username.", parse_mode=ParseMode.HTML)
        context.user_data['action'] = 'awaiting_ban_identity'

    elif query.data.startswith("confirm_ban_"):
        user_id = int(query.data.split("_")[2])
        reason = context.user_data.get('ban_reason', 'No reason provided')
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_banned = TRUE, ban_reason = %s WHERE user_id = %s", (reason, user_id))
        conn.commit()
        cur.close()
        conn.close()

        await query.edit_message_text(f"✅ User <code>{user_id}</code> has been banned.", parse_mode=ParseMode.HTML)
        
        # Notify user
        appeal_keyboard = [[InlineKeyboardButton("📩 Appeal", callback_data=f"appeal_{user_id}")]]
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🚫 <b>You have been banned!</b>\n\n<b>Reason:</b> {reason}\n\nYou can appeal this decision below.",
                reply_markup=InlineKeyboardMarkup(appeal_keyboard),
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

    elif query.data.startswith("appeal_"):
        user_id = int(query.data.split("_")[1])
        await query.edit_message_text("Please send your appeal message now. You can also skip this step.", 
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Skip ⏩", callback_data=f"skip_appeal_{user_id}")]]))
        context.user_data['action'] = 'awaiting_appeal_msg'

    elif query.data.startswith("skip_appeal_"):
        user_id = int(query.data.split("_")[2])
        await query.edit_message_text("Appeal skipped. The owner has been notified.")
        await forward_appeal_to_owner(user_id, "No appeal message provided (Skipped)", context)

    elif query.data.startswith("owner_unban_"):
        user_id = int(query.data.split("_")[2])
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_banned = FALSE, ban_reason = NULL WHERE user_id = %s", (user_id,))
        conn.commit()
        cur.close()
        conn.close()
        await query.edit_message_text(f"✅ User {user_id} has been unbanned.")
        try:
            await context.bot.send_message(user_id, "✅ Your appeal was accepted. You have been unbanned!")
        except: pass

    elif query.data.startswith("owner_notnow_"):
        user_id = int(query.data.split("_")[2])
        # In a real app, we'd use a background task. For now, we'll just set an unban timer in DB.
        import datetime
        unban_at = datetime.datetime.now() + datetime.timedelta(hours=48)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET unban_at = %s WHERE user_id = %s", (unban_at, user_id))
        conn.commit()
        cur.close()
        conn.close()
        await query.edit_message_text(f"🕒 User {user_id} will be automatically unbanned in 48 hours.")

    elif query.data == "get_list":
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users")
        users = cur.fetchall()
        cur.close()
        conn.close()
        
        report_path = "user_report.json"
        with open(report_path, "w") as f:
            json.dump(users, f, default=str, indent=4)
        
        with open(report_path, "rb") as f:
            await context.bot.send_document(chat_id=query.message.chat_id, document=f, filename="users_report.json", caption="📄 Complete User Report")

async def handle_users_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT is_banned FROM users WHERE user_id = %s", (user.id,))
        res = cur.fetchone()
        if res and res[0]:
            await update.message.reply_text("🚫 You are banned from using this bot.")
            cur.close()
            conn.close()
            return
        cur.close()
        conn.close()

    users_shared = update.message.users_shared
    for shared_user in users_shared.users:
        user_id = shared_user.user_id
        try:
            user_chat = await context.bot.get_chat(user_id)
            await show_user_info(update, user_chat, "User Info Found")
        except Exception:
            await update.message.reply_text(
                f"⚠️ <b>Privacy Restricted:</b>\n\n"
                f"🔑 <b>User ID:</b> <code>{user_id}</code>\n\n"
                f"This user is hiding their information due to Telegram's <b>Privacy Settings</b>.\n\n"
                f"✅ <b>Solution:</b> Just <b>Forward</b> any message from this user to me, and I will show you their full details!",
                parse_mode=ParseMode.HTML
            )

async def handle_chat_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT is_banned FROM users WHERE user_id = %s", (user.id,))
        res = cur.fetchone()
        if res and res[0]:
            await update.message.reply_text("🚫 You are banned from using this bot.")
            cur.close()
            conn.close()
            return
        cur.close()
        conn.close()

    chat_id = update.message.chat_shared.chat_id
    try:
        chat = await context.bot.get_chat(chat_id)
        message_text = (
            f"✅ <b>Chat Info Found:</b>\n\n"
            f"🏷️ <b>Title:</b> {html.escape(chat.title or 'N/A')}\n"
            f"🆔 <b>User Name:</b> @{html.escape(chat.username or 'N/A')}\n"
            f"🔑 <b>Chat ID:</b> <code>{chat_id}</code>\n"
            f"👥 <b>Members:</b> {await chat.get_member_count()}\n"
            f"📝 <b>Description:</b> {html.escape(chat.description or 'N/A')}"
        )
        await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)
    except Exception:
        await update.message.reply_text(f"✅ <b>Selected Chat ID:</b> <code>{chat_id}</code>", parse_mode=ParseMode.HTML)

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)
    text = update.message.text
    
    # Check if user is banned
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_banned, unban_at FROM users WHERE user_id = %s", (user.id,))
    res = cur.fetchone()
    if res and res[0]:
        import datetime
        if res[1] and datetime.datetime.now() > res[1]:
            cur.execute("UPDATE users SET is_banned = FALSE, unban_at = NULL WHERE user_id = %s", (user.id,))
            conn.commit()
        else:
            await update.message.reply_text("🚫 You are banned from using this bot.")
            cur.close()
            conn.close()
            return
    cur.close()
    conn.close()

    action = context.user_data.get('action')

    if action == 'awaiting_ban_identity':
        target_id = None
        if update.message.forward_origin and hasattr(update.message.forward_origin, 'sender_user'):
            target_id = update.message.forward_origin.sender_user.id
        elif text.isdigit():
            target_id = int(text)
        elif text.startswith('@'):
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM users WHERE username = %s", (text[1:],))
            row = cur.fetchone()
            if row: target_id = row[0]
            cur.close()
            conn.close()
        
        if target_id:
            context.user_data['target_ban_id'] = target_id
            context.user_data['action'] = 'awaiting_ban_reason'
            await update.message.reply_text(f"Target identified: <code>{target_id}</code>\nNow please enter the <b>Reason</b> for the ban.", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("Could not identify user. Please try forwarding their message or sending their User ID.")

    elif action == 'awaiting_ban_reason':
        context.user_data['ban_reason'] = text
        target_id = context.user_data.get('target_ban_id')
        context.user_data['action'] = None
        keyboard = [[InlineKeyboardButton("✅ Confirm Ban", callback_data=f"confirm_ban_{target_id}")], [InlineKeyboardButton("❌ Cancel", callback_data="users_menu")]]
        await update.message.reply_text(f"❓ <b>Confirm Ban:</b>\n\n<b>User ID:</b> <code>{target_id}</code>\n<b>Reason:</b> {text}", 
                                      reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    elif action == 'awaiting_appeal_msg':
        context.user_data['action'] = None
        await update.message.reply_text("✅ Your appeal has been sent to the owner.")
        await forward_appeal_to_owner(user.id, text, context)

    elif text == "💳 My Account":
        await show_user_info(update, user, "Your Account Info")
    elif update.message.forward_origin:
        origin = update.message.forward_origin
        if hasattr(origin, 'sender_user'):
            await show_user_info(update, origin.sender_user, "Forwarded User Info")
        elif hasattr(origin, 'chat'):
            await update.message.reply_text(f"📢 <b>Forwarded Chat Info:</b>\n🏷️ <b>Title:</b> {html.escape(origin.chat.title)}\n🔑 <b>Chat ID:</b> <code>{origin.chat.id}</code>", parse_mode=ParseMode.HTML)

async def forward_appeal_to_owner(user_id, appeal_msg, context):
    owner_id = int(os.environ.get("OWNER_ID", 0))
    if not owner_id: return
    
    keyboard = [
        [InlineKeyboardButton("✅ Unban", callback_data=f"owner_unban_{user_id}"), 
         InlineKeyboardButton("🕒 Not Now (48h)", callback_data=f"owner_notnow_{user_id}")]
    ]
    await context.bot.send_message(
        chat_id=owner_id,
        text=f"⚖️ <b>New Appeal Received:</b>\n\n<b>User ID:</b> <code>{user_id}</code>\n<b>Message:</b> {appeal_msg}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def show_user_info(update, user, title):
    user_id = user.id
    first_name = html.escape(user.first_name or "N/A")
    last_name = html.escape(user.last_name or "N/A")
    username = html.escape(user.username or "N/A")
    language = html.escape(getattr(user, 'language_code', 'N/A') or 'N/A')
    is_premium = "Yes 🌟" if getattr(user, 'is_premium', False) else "No"
    
    # Try to fetch additional details from database first
    db_bio = "N/A"
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    db_user = cur.fetchone()
    cur.close()
    conn.close()
    
    if db_user:
        db_bio = html.escape(db_user.get('bio') or "N/A")

    # Try to fetch fresh bio from Telegram API if it's missing or if we want latest
    bio = db_bio
    try:
        chat = await update.get_bot().get_chat(user_id)
        if chat.bio:
            bio = html.escape(chat.bio)
            # Update database with new bio
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("UPDATE users SET bio = %s WHERE user_id = %s", (chat.bio, user_id))
            conn.commit()
            cur.close()
            conn.close()
    except Exception:
        pass

    message_text = (
        f"👤 <b>{title}:</b>\n\n"
        f"👤 <b>First Name:</b> {first_name}\n"
        f"👤 <b>Last Name:</b> {last_name}\n"
        f"🆔 <b>User Name:</b> @{username}\n"
        f"🔑 <b>User ID:</b> <code>{user_id}</code>\n"
        f"🌐 <b>Language:</b> {language}\n"
        f"🌟 <b>Premium:</b> {is_premium}\n"
        f"📝 <b>Bio:</b> {bio}\n\n"
        f"🔗 <b>Permanent Link:</b> <a href='tg://user?id={user_id}'>Click Here</a>"
    )
    
    await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)

if __name__ == '__main__':
    init_db()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.StatusUpdate.USERS_SHARED, handle_users_shared))
    application.add_handler(MessageHandler(filters.StatusUpdate.CHAT_SHARED, handle_chat_shared))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    print("Bot is starting...")
    application.run_polling()
