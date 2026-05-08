#!/usr/bin/env python3
"""
Telegram 个人工具箱 Bot - 完整可运行版
"""

import logging
import os
import uuid
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

from config import TELEGRAM_TOKEN, OWNER_CHAT_ID, PUBLIC_BASE_URL, IMAGES_DIR
from database import (
    init_db, add_note, get_all_notes, get_note, update_note, delete_note,
    add_bookmark, get_all_bookmarks, get_bookmark, update_bookmark, delete_bookmark
)
from web import app as flask_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADD_NOTE_TITLE, ADD_NOTE_CONTENT = range(2)
ADD_BOOKMARK_URL, ADD_BOOKMARK_REMARK = range(2, 4)

async def check_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if update.effective_user.id != OWNER_CHAT_ID:
        await update.message.reply_text("⛔ 仅限主人使用")
        return False
    return True

def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📷 图床", callback_data="menu_images")],
        [InlineKeyboardButton("📝 记事本", callback_data="menu_notes")],
        [InlineKeyboardButton("🔖 收藏夹", callback_data="menu_bookmarks")],
        [InlineKeyboardButton("☁️ 备份", callback_data="menu_backup")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context): return
    await update.message.reply_text(
        "👋 **欢迎使用 Telegram 个人工具箱**！\n点击下方按钮使用：",
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_CHAT_ID: return
    data = query.data

    if data == "menu_images":
        await query.edit_message_text("📷 **图床**\n直接发送图片即可上传\n发送 /images 查看列表", reply_markup=get_main_menu_keyboard())
    elif data == "menu_notes":
        notes = get_all_notes()
        await query.edit_message_text(f"📝 **记事本** ({len(notes)} 条)\n使用 /addnote 添加", reply_markup=get_main_menu_keyboard())
    elif data == "menu_bookmarks":
        bookmarks = get_all_bookmarks()
        await query.edit_message_text(f"🔖 **收藏夹** ({len(bookmarks)} 条)\n使用 /addbookmark 添加", reply_markup=get_main_menu_keyboard())
    elif data == "menu_backup":
        await query.edit_message_text("☁️ **备份管理**\n使用 /backup 立即备份", reply_markup=get_main_menu_keyboard())

# ==================== 图床 ====================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context): return
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(IMAGES_DIR, filename)
    await file.download_to_drive(filepath)
    image_url = f"{PUBLIC_BASE_URL}/images/{filename}"
    await update.message.reply_text(f"✅ 上传成功！\n🔗 {image_url}", parse_mode=ParseMode.MARKDOWN)

# ==================== 记事本 ====================
async def add_note_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context): return ConversationHandler.END
    await update.message.reply_text("📝 请输入记事标题：")
    return ADD_NOTE_TITLE

async def add_note_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['note_title'] = update.message.text.strip()
    await update.message.reply_text("✅ 标题已记录！请输入内容：")
    return ADD_NOTE_CONTENT

async def add_note_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = context.user_data['note_title']
    content = update.message.text.strip()
    note_id = add_note(title, content)
    await update.message.reply_text(f"✅ 添加成功！ID: {note_id}\n发送 /notes 查看")
    context.user_data.clear()
    return ConversationHandler.END

async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context): return
    notes = get_all_notes()
    if not notes:
        await update.message.reply_text("📭 还没有记事")
        return
    text = "📝 **所有记事本**：\n\n"
    for note in notes:
        text += f"**#{note['id']}** {note['title']}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ==================== 收藏夹 ====================
async def add_bookmark_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context): return ConversationHandler.END
    await update.message.reply_text("🔖 请输入收藏 URL：")
    return ADD_BOOKMARK_URL

async def add_bookmark_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bookmark_url'] = update.message.text.strip()
    await update.message.reply_text("✅ URL已记录！请输入标题：")
    return ADD_BOOKMARK_REMARK

async def add_bookmark_remark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    url = context.user_data['bookmark_url']
    bookmark_id = add_bookmark(title, url)
    await update.message.reply_text(f"✅ 添加成功！ID: {bookmark_id}\n发送 /bookmarks 查看")
    context.user_data.clear()
    return ConversationHandler.END

async def list_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context): return
    bookmarks = get_all_bookmarks()
    if not bookmarks:
        await update.message.reply_text("📭 还没有收藏")
        return
    text = "🔖 **所有收藏夹**：\n\n"
    for bm in bookmarks:
        text += f"**#{bm['id']}** {bm['title']}\n🔗 {bm['url']}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

# ==================== 主程序 ====================
def main():
    init_db()
    def run_flask():
        flask_app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
    Thread(target=run_flask, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("notes", list_notes))
    application.add_handler(CommandHandler("bookmarks", list_bookmarks))
    application.add_handler(CommandHandler("addnote", add_note_start))
    application.add_handler(CommandHandler("addbookmark", add_bookmark_start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    note_conv = ConversationHandler(
        entry_points=[CommandHandler("addnote", add_note_start)],
        states={
            ADD_NOTE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_note_title)],
            ADD_NOTE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_note_content)],
        },
        fallbacks=[],
    )
    application.add_handler(note_conv)

    bookmark_conv = ConversationHandler(
        entry_points=[CommandHandler("addbookmark", add_bookmark_start)],
        states={
            ADD_BOOKMARK_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_bookmark_url)],
            ADD_BOOKMARK_REMARK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_bookmark_remark)],
        },
        fallbacks=[],
    )
    application.add_handler(bookmark_conv)

    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()

if __name__ == "__main__":
    main()