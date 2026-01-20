from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonRequestUsers, KeyboardButtonRequestChat, ChatAdministratorRights, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ParseMode

import os
import logging
import html
import json
import sqlite3
from flask import Flask
from threading import Thread

# Flask server for keeping the bot alive
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    flask_app.run(host='0.0.0.0', port=5000)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def get_db_connection():
    conn = sqlite3.connect("bot_database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            language_code TEXT,
            is_premium INTEGER,
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT,
            unban_at TIMESTAMP,
            bio TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_user(user):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, first_name, last_name, username, language_code, is_premium)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (user_id) DO UPDATE SET
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            username = EXCLUDED.username,
            language_code = EXCLUDED.language_code,
            is_premium = EXCLUDED.is_premium
    """, (user.id, user.first_name, user.last_name, user.username, user.language_code, 1 if user.is_premium else 0))
    conn.commit()
    conn.close()

OWNER_ID = int(os.environ.get("OWNER_ID", 0))
BACKUP_CHANNEL_ID = os.environ.get("BACKUP_CHANNEL_ID")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)
    
    if context.bot_data.get('startup_checked') is None:
        context.bot_data['startup_checked'] = True
        backup_path = "user_report.json"
        if os.path.exists(backup_path):
            logging.info("Backup file found on startup. Importing...")
            try:
                with open(backup_path, 'r') as f:
                    data = json.load(f)
                    conn = get_db_connection()
                    cur = conn.cursor()
                    for u in data:
                        cur.execute("""
                            INSERT INTO users (user_id, first_name, last_name, username, language_code, is_premium, is_banned, ban_reason, bio)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT (user_id) DO UPDATE SET
                                first_name = EXCLUDED.first_name,
                                last_name = EXCLUDED.last_name,
                                username = EXCLUDED.username,
                                is_premium = EXCLUDED.is_premium,
                                is_banned = EXCLUDED.is_banned,
                                ban_reason = EXCLUDED.ban_reason,
                                bio = EXCLUDED.bio
                        """, (u['user_id'], u['first_name'], u['last_name'], u['username'], u.get('language_code'), u['is_premium'], 1 if u['is_banned'] else 0, u['ban_reason'], u.get('bio')))
                    conn.commit()
                    conn.close()
                logging.info("Startup backup import completed.")
            except Exception as e:
                logging.error(f"Error importing backup on startup: {e}")

    admin_rights = ChatAdministratorRights(
        is_anonymous=False, can_manage_chat=True, can_delete_messages=False, can_manage_video_chats=False,
        can_restrict_members=False, can_promote_members=False, can_change_info=False, can_invite_users=False,
        can_post_messages=False, can_edit_messages=False, can_pin_messages=False, can_post_stories=False,
        can_edit_stories=False, can_delete_stories=False, can_manage_topics=False
    )

    reply_keyboard = [
        [KeyboardButton("👤 User", request_users=KeyboardButtonRequestUsers(request_id=1, user_is_bot=False, max_quantity=1)),
         KeyboardButton("🌟 Premium", request_users=KeyboardButtonRequestUsers(request_id=2, user_is_premium=True, max_quantity=1)),
         KeyboardButton("🤖 Bot", request_users=KeyboardButtonRequestUsers(request_id=3, user_is_bot=True, max_quantity=1))],
        [KeyboardButton("👥 Group", request_chat=KeyboardButtonRequestChat(request_id=4, chat_is_channel=False)),
         KeyboardButton("📢 Channel", request_chat=KeyboardButtonRequestChat(request_id=5, chat_is_channel=True)),
         KeyboardButton("🏛️ Forum", request_chat=KeyboardButtonRequestChat(request_id=6, chat_is_channel=False, chat_is_forum=True))],
        [KeyboardButton("🏘️ My Group", request_chat=KeyboardButtonRequestChat(request_id=7, chat_is_channel=False, user_administrator_rights=admin_rights)),
         KeyboardButton("📡 My Channel", request_chat=KeyboardButtonRequestChat(request_id=8, chat_is_channel=True, user_administrator_rights=admin_rights)),
         KeyboardButton("🗯️ My Forum", request_chat=KeyboardButtonRequestChat(request_id=9, chat_is_channel=False, chat_is_forum=True, user_administrator_rights=admin_rights))],
        [KeyboardButton("💳 My Account")]
    ]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    if user.id == OWNER_ID:
        inline_keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data="status")],
            [InlineKeyboardButton("👥 Users", callback_data="users_menu"), InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")]
        ]
        inline_markup = InlineKeyboardMarkup(inline_keyboard)
        await update.message.reply_text("👑 <b>Welcome Owner!</b>\nYour Dashboard is ready.", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        await update.message.reply_text("🛠 <b>Admin Panel:</b>", reply_markup=inline_markup, parse_mode=ParseMode.HTML)
    else:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT is_banned FROM users WHERE user_id = ?", (user.id,))
        res = cur.fetchone()
        if res and res[0]:
            await update.message.reply_text("🚫 You are banned from using this bot.")
            conn.close()
            return
        conn.close()
        await show_user_info(update, user, "Your Profile Info")
        await update.message.reply_text("Choose an option from the menu below:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("restore_"):
        file_path = query.data.split("_", 1)[1]
        if not os.path.exists(file_path):
            await query.answer("❌ Local file not found.", show_alert=True)
            return
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM users")
                for u in data:
                    cur.execute("""
                        INSERT INTO users (user_id, first_name, last_name, username, language_code, is_premium, is_banned, ban_reason, bio)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (u['user_id'], u['first_name'], u['last_name'], u['username'], u.get('language_code'), u['is_premium'], u['is_banned'], u['ban_reason'], u.get('bio')))
                conn.commit()
                conn.close()
            await query.edit_message_caption(caption=query.message.caption + "\n\n✅ <b>Restored Successfully!</b>", parse_mode=ParseMode.HTML)
        except Exception as e:
            await query.answer(f"❌ Restore Failed: {e}", show_alert=True)

    elif query.data == "status":
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        conn.close()
        await query.edit_message_text(f"📊 <b>Bot Status:</b>\nTotal Users: {count}", parse_mode=ParseMode.HTML)
    
    elif query.data == "users_menu":
        keyboard = [
            [InlineKeyboardButton("🚫 Ban User", callback_data="ban_start"), InlineKeyboardButton("✅ Unban User", callback_data="unban")],
            [InlineKeyboardButton("ℹ️ Get Info", callback_data="get_info"), InlineKeyboardButton("📄 Get User List", callback_data="get_list")]
        ]
        await query.edit_message_text("👥 <b>User Management:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif query.data == "ban_start":
        await query.edit_message_text("🚫 <b>Ban User:</b>\nForward a message or send ID/Username.", parse_mode=ParseMode.HTML)
        context.user_data['action'] = 'awaiting_ban_identity'

    elif query.data.startswith("confirm_ban_"):
        user_id = int(query.data.split("_")[2])
        reason = context.user_data.get('ban_reason', 'No reason provided')
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_banned = 1, ban_reason = ? WHERE user_id = ?", (reason, user_id))
        conn.commit()
        conn.close()
        await query.edit_message_text(f"✅ User <code>{user_id}</code> banned.", parse_mode=ParseMode.HTML)
        try:
            await context.bot.send_message(chat_id=user_id, text=f"🚫 <b>Banned!</b>\nReason: {reason}", parse_mode=ParseMode.HTML)
        except: pass

    elif query.data.startswith("owner_unban_"):
        user_id = int(query.data.split("_")[2])
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_banned = 0, ban_reason = NULL WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await query.edit_message_text(f"✅ User {user_id} unbanned.")

    elif query.data == "broadcast":
        await query.edit_message_text("📢 <b>Broadcast:</b> Send your message.", parse_mode=ParseMode.HTML)
        context.user_data['action'] = 'awaiting_broadcast_msg'

    elif query.data == "get_info":
        await query.edit_message_text("ℹ️ <b>Get Info:</b> Send ID/Username.", parse_mode=ParseMode.HTML)
        context.user_data['action'] = 'awaiting_info_lookup'
    
    elif query.data == "get_list":
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users")
        users = [dict(row) for row in cur.fetchall()]
        conn.close()
        path = "user_report.json"
        with open(path, "w") as f: json.dump(users, f, default=str, indent=4)
        with open(path, "rb") as f:
            await context.bot.send_document(chat_id=query.message.chat_id, document=f, filename="users_report.json")

async def handle_users_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT is_banned FROM users WHERE user_id = ?", (user.id,))
        res = cur.fetchone()
        if res and res[0]:
            await update.message.reply_text("🚫 Banned.")
            conn.close()
            return
        conn.close()

    for shared_user in update.message.users_shared.users:
        try:
            await show_user_info(update, shared_user, "User Info")
        except:
            await update.message.reply_text(f"🔑 ID: <code>{shared_user.user_id}</code> (Privacy Restricted)", parse_mode=ParseMode.HTML)

async def handle_chat_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_shared.chat_id
    try:
        chat = await context.bot.get_chat(chat_id)
        msg = (f"✅ <b>Chat Info:</b>\n🏷️ Title: {html.escape(chat.title or 'N/A')}\n🆔 @{html.escape(chat.username or 'N/A')}\n🔑 ID: <code>{chat_id}</code>")
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    except:
        await update.message.reply_text(f"✅ ID: <code>{chat_id}</code>", parse_mode=ParseMode.HTML)

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)
    text = update.message.text
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_banned, unban_at FROM users WHERE user_id = ?", (user.id,))
    res = cur.fetchone()
    if res and res[0]:
        import datetime
        if res[1] and datetime.datetime.now() > datetime.datetime.fromisoformat(res[1]):
            cur.execute("UPDATE users SET is_banned = 0, unban_at = NULL WHERE user_id = ?", (user.id,))
            conn.commit()
        else:
            await update.message.reply_text("🚫 Banned.")
            conn.close()
            return
    conn.close()

    action = context.user_data.get('action')
    if action == 'awaiting_info_lookup':
        context.user_data['action'] = None
        target_id = None
        if text.isdigit(): target_id = int(text)
        elif text.startswith('@'):
            conn = get_db_connection()
            cur = conn.cursor(); cur.execute("SELECT user_id FROM users WHERE username = ?", (text[1:],))
            row = cur.fetchone(); conn.close()
            if row: target_id = row[0]
        if target_id:
            try:
                class MockUser:
                    def __init__(self, id): self.id = id
                await show_user_info(update, MockUser(target_id), "Lookup")
            except: pass
        else: await update.message.reply_text("❌ Not found.")

    elif action == 'awaiting_broadcast_msg':
        context.user_data['action'] = None
        await update.message.reply_text("🚀 Broadcasting...")
        conn = get_db_connection()
        cur = conn.cursor(); cur.execute("SELECT user_id FROM users")
        users = [dict(row) for row in cur.fetchall()]; conn.close()
        for u in users:
            try: await context.bot.send_message(chat_id=u['user_id'], text=text, parse_mode=ParseMode.HTML)
            except: pass
        await update.message.reply_text("🏁 Done.")

    elif text == "💳 My Account": await show_user_info(update, user, "My Account")
    elif update.message.forward_origin:
        origin = update.message.forward_origin
        if hasattr(origin, 'sender_user'): await show_user_info(update, origin.sender_user, "Forwarded User")

async def forward_appeal_to_owner(user_id, appeal_msg, context):
    owner_id = int(os.environ.get("OWNER_ID", 0))
    if not owner_id: return
    keyboard = [[InlineKeyboardButton("✅ Unban", callback_data=f"owner_unban_{user_id}")]]
    await context.bot.send_message(chat_id=owner_id, text=f"⚖️ Appeal: {user_id}\nMsg: {appeal_msg}", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_user_info(update, user, title):
    user_id = getattr(user, 'id', getattr(user, 'user_id', None))
    first_name = html.escape(getattr(user, 'first_name', "") or "N/A")
    last_name = html.escape(getattr(user, 'last_name', "") or "N/A")
    username = html.escape(getattr(user, 'username', "") or "N/A")
    language = html.escape(getattr(user, 'language_code', "") or 'N/A')
    raw_is_premium = getattr(user, 'is_premium', False)
    bio = "N/A"
    try:
        chat = await update.get_bot().get_chat(user_id)
        first_name = html.escape(chat.first_name or first_name)
        last_name = html.escape(chat.last_name or last_name)
        username = html.escape(chat.username or username)
        bio = html.escape(chat.bio or "N/A")
        if hasattr(chat, 'is_premium') and chat.is_premium is not None: raw_is_premium = chat.is_premium
    except: pass
    is_premium_text = "Yes 🌟" if raw_is_premium else "No"
    msg = (f"👤 <b>{title}:</b>\n\n🏷️ FN: {first_name}\n🏷️ LN: {last_name}\n🆔 UN: @{username}\n🔑 ID: <code>{user_id}</code>\n🌐 Lang: {language}\n🌟 Prem: {is_premium_text}\n📝 Bio: {bio}")
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def daily_backup(context: ContextTypes.DEFAULT_TYPE):
    target_id = BACKUP_CHANNEL_ID or os.environ.get("OWNER_ID", 0)
    if not target_id:
        logging.warning("No BACKUP_CHANNEL_ID or OWNER_ID set. Backup skipped.")
        return
    try:
        # Check if chat is accessible
        try:
            await context.bot.get_chat(target_id)
        except Exception:
            logging.error(f"Backup Error: Chat {target_id} not found or bot is not a member. Please add the bot as an admin.")
            return

        conn = get_db_connection()
        cur = conn.cursor(); cur.execute("SELECT * FROM users")
        users = [dict(row) for row in cur.fetchall()]; conn.close()
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"backup_{timestamp}.json"
        with open(path, "w") as f: json.dump(users, f, default=str, indent=4)
        keyboard = [[InlineKeyboardButton("🔄 Restore", callback_data=f"restore_{path}")]]
        with open(path, "rb") as f:
            await context.bot.send_document(chat_id=target_id, document=f, filename=f"backup_{timestamp}.json",
                                            caption=f"📅 <b>Database Backup</b>\nTime: {timestamp}",
                                            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    except Exception as e: logging.error(f"Backup Error: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Error {context.error}")

def main():
    init_db()
    keep_alive()
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logging.error("TELEGRAM_BOT_TOKEN not found!")
        return
    application = ApplicationBuilder().token(token).build()
    application.job_queue.run_repeating(daily_backup, interval=600, first=10)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.StatusUpdate.USERS_SHARED, handle_users_shared))
    application.add_handler(MessageHandler(filters.StatusUpdate.CHAT_SHARED, handle_chat_shared))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    application.add_error_handler(error_handler)
    print("Bot starting...")
    application.run_polling()

if __name__ == '__main__':
    main()