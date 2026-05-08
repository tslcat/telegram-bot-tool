#!/usr/bin/env python3
"""
Telegram 个人工具箱 Bot - 修复版（记事本 + 收藏夹添加正常显示）
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

from config import TELEGRAM_TOKEN, OWNER_CHAT_ID, PUBLIC_BASE_URL, IMAGES_DIR, BACKUP_INTERVAL_HOURS
from database import (
    init_db, add_note, get_all_notes, get_note, update_note, delete_note,
    add_bookmark, get_all_bookmarks, get_bookmark, update_bookmark, delete_bookmark
)
from webdav_backup import backup_now, restore_from_zip, create_backup_zip
from web import app as flask_app

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 状态
ADD_NOTE_TITLE, ADD_NOTE_CONTENT = range(2)
ADD_BOOKMARK_URL, ADD_BOOKMARK_REMARK = range(2, 4)

async def check_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if update.effective_user.id != OWNER_CHAT_ID:
        await update.message.reply_text("⛔ 此 Bot 仅限主人使用。")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return
    keyboard = [
        [InlineKeyboardButton("📷 图床管理", callback_data="menu_images")],
        [InlineKeyboardButton("📝 记事本", callback_data="menu_notes")],
        [InlineKeyboardButton("🔖 收藏夹", callback_data="menu_bookmarks")],
        [InlineKeyboardButton("☁️ 备份管理", callback_data="menu_backup")],
    ]
    await update.message.reply_text(
        "👋 欢迎使用 **Telegram 个人工具箱**！\n\n请选择功能：",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_CHAT_ID:
        return
    data = query.data

    if data == "menu_images":
        await show_images_menu(query)
    elif data == "menu_notes":
        await show_notes_menu(query)
    elif data == "menu_bookmarks":
        await show_bookmarks_menu(query)
    elif data == "menu_backup":
        await show_backup_menu(query)
    elif data.startswith("note_delete_"):
        note_id = int(data.split("_")[2])
        delete_note(note_id)
        await query.edit_message_text(f"✅ 已删除记事 #{note_id}")
    elif data.startswith("bookmark_delete_"):
        bm_id = int(data.split("_")[2])
        delete_bookmark(bm_id)
        await query.edit_message_text(f"✅ 已删除收藏 #{bm_id}")
    elif data == "back_main":
        await show_main_menu(query)

async def show_main_menu(query):
    keyboard = [
        [InlineKeyboardButton("📷 图床管理", callback_data="menu_images")],
        [InlineKeyboardButton("📝 记事本", callback_data="menu_notes")],
        [InlineKeyboardButton("🔖 收藏夹", callback_data="menu_bookmarks")],
        [InlineKeyboardButton("☁️ 备份管理", callback_data="menu_backup")],
    ]
    await query.edit_message_text(
        "👋 欢迎使用 **Telegram 个人工具箱**！\n请选择功能：",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def show_notes_menu(query):
    notes = get_all_notes()
    keyboard = [
        [InlineKeyboardButton("➕ 添加新记事（请用 /addnote 命令）", callback_data="noop")],
        [InlineKeyboardButton("📋 查看所有记事", callback_data="list_notes")],
        [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_main")],
    ]
    text = f"📝 **记事本** ({len(notes)} 条记录)\n\n请使用命令 `/addnote` 添加"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def show_bookmarks_menu(query):
    bookmarks = get_all_bookmarks()
    keyboard = [
        [InlineKeyboardButton("➕ 添加新收藏（请用 /addbookmark 命令）", callback_data="noop")],
        [InlineKeyboardButton("📋 查看所有收藏", callback_data="list_bookmarks")],
        [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_main")],
    ]
    text = f"🔖 **收藏夹** ({len(bookmarks)} 条记录)\n\n请使用命令 `/addbookmark` 添加"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# ==================== 图床 ====================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(IMAGES_DIR, filename)
    await file.download_to_drive(filepath)
    image_url = f"{PUBLIC_BASE_URL}/images/{filename}"
    await update.message.reply_text(
        f"✅ **图片上传成功！**\n\n🔗 `{image_url}`",
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== 记事本 ====================
async def add_note_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return ConversationHandler.END
    await update.message.reply_text("📝 **添加新记事**\n\n请先输入标题：")
    return ADD_NOTE_TITLE

async def add_note_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['note_title'] = update.message.text.strip()
    await update.message.reply_text("✅ 标题已记录！\n\n现在请输入内容（支持多行）：")
    return ADD_NOTE_CONTENT

async def add_note_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = context.user_data['note_title']
    content = update.message.text.strip()
    note_id = add_note(title, content)
    await update.message.reply_text(
        f"✅ **记事添加成功！**\n\nID: `{note_id}`\n标题: {title}\n\n发送 `/notes` 查看全部",
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data.clear()
    return ConversationHandler.END

async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return
    notes = get_all_notes()
    if not notes:
        await update.message.reply_text("📭 还没有任何记事")
        return
    text = "📝 **所有记事本**：\n\n"
    for note in notes:
        text += f"**#{note['id']}** {note['title']}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ==================== 收藏夹 ====================
async def add_bookmark_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return ConversationHandler.END
    await update.message.reply_text("🔖 **添加新收藏**\n\n请发送 URL：")
    return ADD_BOOKMARK_URL

async def add_bookmark_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data['bookmark_url'] = url
    await update.message.reply_text("✅ URL 已记录！\n\n请输入标题：")
    return ADD_BOOKMARK_REMARK

async def add_bookmark_remark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    url = context.user_data['bookmark_url']
    bookmark_id = add_bookmark(title, url)
    await update.message.reply_text(
        f"✅ **收藏添加成功！**\n\nID: `{bookmark_id}`\n标题: {title}\n发送 `/bookmarks` 查看",
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data.clear()
    return ConversationHandler.END

async def list_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return
    bookmarks = get_all_bookmarks()
    if not bookmarks:
        await update.message.reply_text("📭 还没有任何收藏")
        return
    text = "🔖 **所有收藏夹**：\n\n"
    for bm in bookmarks:
        text += f"**#{bm['id']}** {bm['title']}\n🔗 {bm['url']}\n\n"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

# ==================== 主程序 ====================
def main():
    init_db()

    def run_flask():
        flask_app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

    Thread(target=run_flask, daemon=True).start()
    logger.info("Flask Web 服务器已启动")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("notes", list_notes))
    application.add_handler(CommandHandler("bookmarks", list_bookmarks))
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

    logger.info("Bot 启动中...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()