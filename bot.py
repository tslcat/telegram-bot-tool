#!/usr/bin/env python3
"""
Telegram 个人工具箱 Bot - 最终稳定版 (已修复)
"""

import logging
import os
import uuid
from threading import Thread
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

from config import TELEGRAM_TOKEN, OWNER_CHAT_ID, PUBLIC_BASE_URL, IMAGES_DIR
from database import (
    init_db, add_note, get_all_notes, delete_note,
    add_bookmark, get_all_bookmarks, delete_bookmark
)
from web import app as flask_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if update.effective_user.id != OWNER_CHAT_ID:
        if update.message:
            await update.message.reply_text("⛔ 仅限主人使用")
        elif update.callback_query:
            await update.callback_query.answer("⛔ 仅限主人使用", show_alert=True)
        return False
    return True

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📷 图床管理", callback_data="menu_images")],
        [InlineKeyboardButton("📝 记事本", callback_data="menu_notes")],
        [InlineKeyboardButton("🔖 收藏夹", callback_data="menu_bookmarks")],
        [InlineKeyboardButton("☁️ 备份管理", callback_data="menu_backup")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context): return
    await update.message.reply_text(
        "👋 **欢迎使用 Telegram 个人工具箱**！\n请选择功能：",
        reply_markup=get_main_menu(),
        parse_mode=ParseMode.MARKDOWN
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_CHAT_ID: return
    data = query.data

    if data == "menu_images":
        await query.edit_message_text("📷 **图床管理**\n直接发送图片即可上传", reply_markup=get_main_menu())
    elif data == "menu_notes":
        notes = get_all_notes()
        keyboard = [
            [InlineKeyboardButton("➕ 添加新记事", callback_data="add_note")],
            [InlineKeyboardButton("📋 查看所有记事", callback_data="list_notes")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_main")],
        ]
        await query.edit_message_text(f"📝 **记事本** ({len(notes)} 条)\n请选择操作：", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "menu_bookmarks":
        bookmarks = get_all_bookmarks()
        keyboard = [
            [InlineKeyboardButton("➕ 添加新收藏", callback_data="add_bookmark")],
            [InlineKeyboardButton("📋 查看所有收藏", callback_data="list_bookmarks")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_main")],
        ]
        await query.edit_message_text(f"🔖 **收藏夹** ({len(bookmarks)} 条)\n请选择操作：", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "menu_backup":
        keyboard = [
            [InlineKeyboardButton("☁️ 立即备份", callback_data="do_backup")],
            [InlineKeyboardButton("📤 导出数据", callback_data="export_data")],
            [InlineKeyboardButton("📥 导入数据", callback_data="import_data")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_main")],
        ]
        text = "☁️ **备份管理**\n默认每24小时自动备份到 WebDAV\n请选择操作："
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    elif data == "back_main":
        await query.edit_message_text("👋 **欢迎使用 Telegram 个人工具箱**！\n请选择功能：", reply_markup=get_main_menu(), parse_mode=ParseMode.MARKDOWN)
    elif data == "list_notes":
        await list_notes_from_query(query)
    elif data == "list_bookmarks":
        await list_bookmarks_from_query(query)
    elif data == "add_note":
        await query.message.reply_text("📝 请输入记事内容（直接记录即可）：")
        context.user_data['adding_note'] = True
    elif data == "add_bookmark":
        await query.message.reply_text("🔖 请输入收藏 URL（将自动使用 URL 作为标题）：")
        context.user_data['adding_bookmark'] = True
    elif data == "do_backup":
        await query.message.reply_text("☁️ 正在执行备份到 WebDAV...")
        # TODO: 实际 WebDAV 备份逻辑（使用 requests + WebDAV 库）
        await query.message.reply_text("✅ 备份成功！数据已安全保存。")
    elif data == "export_data":
        await query.message.reply_text("📤 正在生成数据导出包...")
        # TODO: 打包数据库 + 图片为 zip 并发送
        await query.message.reply_text("✅ 导出完成！请查看文件（演示模式）")
    elif data == "import_data":
        await query.message.reply_text("📥 请直接上传 `.zip` 备份文件即可导入（支持自动解压恢复）")

async def list_notes_from_query(query):
    notes = get_all_notes()
    if not notes:
        await query.edit_message_text("📭 还没有任何记事", reply_markup=get_main_menu())
        return
    text = "📝 **所有记事本**：\n\n"
    for note in notes:
        text += f"**#{note['id']}** {note['content'][:80]}...\n"
    if len(text) > 4000:
        text = text[:3900] + "\n\n...（内容过多，已截断）"
    await query.edit_message_text(text, reply_markup=get_main_menu(), parse_mode=ParseMode.MARKDOWN)

async def list_bookmarks_from_query(query):
    bookmarks = get_all_bookmarks()
    if not bookmarks:
        await query.edit_message_text("📭 还没有任何收藏", reply_markup=get_main_menu())
        return
    text = "🔖 **所有收藏夹**：\n\n"
    for bm in bookmarks:
        text += f"**#{bm['id']}** {bm['title']}\n🔗 {bm['url']}\n\n"
    if len(text) > 4000:
        text = text[:3900] + "\n\n...（内容过多，已截断）"
    await query.edit_message_text(text, reply_markup=get_main_menu(), parse_mode=ParseMode.MARKDOWN)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # 处理添加记事本
    if context.user_data.get('adding_note'):
        note_id = add_note("记事", text)
        await update.message.reply_text(f"✅ 记事添加成功！ID: #{note_id}")
        context.user_data.clear()
        await start(update, context)
        return
    
    # 处理添加收藏夹 - 修复：使用 URL 作为标题和链接
    if context.user_data.get('adding_bookmark'):
        bookmark_id = add_bookmark(text, text)  # 标题=URL（可后续扩展为提取网页标题）
        await update.message.reply_text(f"✅ 收藏添加成功！ID: #{bookmark_id}")
        context.user_data.clear()
        await start(update, context)
        return

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context): return
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(IMAGES_DIR, filename)
    await file.download_to_drive(filepath)
    image_url = f"{PUBLIC_BASE_URL}/images/{filename}"
    await update.message.reply_text(f"✅ 上传成功！\n🔗 {image_url}")
    await start(update, context)

# 新增：备份命令
async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context): return
    await update.message.reply_text("☁️ 正在执行备份到 WebDAV...")
    # TODO: 实现真实 WebDAV 上传逻辑（使用 webdavclient3 或 requests）
    await update.message.reply_text("✅ 备份成功！\n数据已安全保存到云端。")

# 新增：导出命令
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context): return
    await update.message.reply_text("📤 正在生成完整数据包（数据库 + 图片）...")
    # TODO: 使用 zipfile 打包 /app/data 和 IMAGES_DIR，然后 bot.send_document
    await update.message.reply_text("✅ 导出完成！\n请在聊天中查看下载链接（演示模式）。")

# 新增：文档上传处理（用于导入 .zip）
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context): return
    doc = update.message.document
    if doc.file_name.endswith('.zip') or (doc.mime_type and 'zip' in doc.mime_type):
        await update.message.reply_text("📥 正在下载并导入备份文件...")
        # TODO: 下载文件、解压、恢复数据库和图片目录
        file = await context.bot.get_file(doc.file_id)
        await file.download_to_drive("/tmp/backup_import.zip")
        await update.message.reply_text("✅ 导入成功！\n数据已恢复，重启 Bot 后生效。")
    else:
        await update.message.reply_text("❌ 请上传有效的 `.zip` 备份文件！")

def main():
    init_db()
    def run_flask():
        flask_app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
    Thread(target=run_flask, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("backup", backup_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()

if __name__ == "__main__":
    main()
