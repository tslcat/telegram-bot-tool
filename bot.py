#!/usr/bin/env python3
"""
Telegram 个人工具箱 Bot
支持图床、记事本、收藏夹 + WebDAV 备份
"""

import logging
import os
import uuid
from datetime import datetime
from threading import Thread
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

from config import (
    TELEGRAM_TOKEN, OWNER_CHAT_ID, PUBLIC_BASE_URL,
    IMAGES_DIR, BACKUP_INTERVAL_HOURS
)
from database import (
    init_db, add_note, get_all_notes, get_note, update_note, delete_note,
    add_bookmark, get_all_bookmarks, get_bookmark, update_bookmark, delete_bookmark
)
from webdav_backup import backup_now, restore_from_zip, create_backup_zip
from web import app as flask_app

# 日志配置
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 状态常量
ADD_NOTE_TITLE, ADD_NOTE_CONTENT = range(2)
ADD_BOOKMARK_URL, ADD_BOOKMARK_REMARK = range(2, 4)
EDIT_NOTE_TITLE, EDIT_NOTE_CONTENT = range(4, 6)
EDIT_BOOKMARK = range(6, 9)  # 简化处理

# ==================== 权限检查 ====================
async def check_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """检查是否为所有者"""
    if update.effective_user.id != OWNER_CHAT_ID:
        await update.message.reply_text("⛔ 抱歉，此 Bot 仅限主人使用。")
        return False
    return True

# ==================== 主菜单 ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return
    
    keyboard = [
        [InlineKeyboardButton("📷 图床管理", callback_data="menu_images")],
        [InlineKeyboardButton("📝 记事本", callback_data="menu_notes")],
        [InlineKeyboardButton("🔖 收藏夹", callback_data="menu_bookmarks")],
        [InlineKeyboardButton("☁️ 备份管理", callback_data="menu_backup")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 欢迎使用 **Telegram 个人工具箱**！\n\n"
        "请选择功能：",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != OWNER_CHAT_ID:
        await query.edit_message_text("⛔ 权限不足")
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
    elif data.startswith("note_"):
        await handle_note_action(query, data)
    elif data.startswith("bookmark_"):
        await handle_bookmark_action(query, data)
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
        "👋 欢迎使用 **Telegram 个人工具箱**！\n\n请选择功能：",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== 图床功能 ====================
async def show_images_menu(query):
    keyboard = [
        [InlineKeyboardButton("📤 上传新图片（直接发送图片即可）", callback_data="noop")],
        [InlineKeyboardButton("📋 查看图片列表", callback_data="list_images")],
        [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_main")],
    ]
    await query.edit_message_text(
        "📷 **图床管理**\n\n"
        "• 直接在聊天中发送图片即可自动上传\n"
        "• 图片将保存在服务器并生成公开链接\n"
        "• 链接格式：{}/images/文件名".format(PUBLIC_BASE_URL),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return
    
    photo = update.message.photo[-1]  # 最高分辨率
    file = await context.bot.get_file(photo.file_id)
    
    # 生成唯一文件名
    ext = ".jpg"  # Telegram 图片通常是 jpg
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(IMAGES_DIR, filename)
    
    # 下载图片
    await file.download_to_drive(filepath)
    
    # 生成公开链接
    image_url = f"{PUBLIC_BASE_URL}/images/{filename}"
    
    await update.message.reply_text(
        f"✅ **图片上传成功！**\n\n"
        f"🔗 公开链接：\n`{image_url}`\n\n"
        f"📁 文件名：`{filename}`\n"
        f"💡 提示：可直接复制链接使用",
        parse_mode=ParseMode.MARKDOWN
    )
    logger.info(f"用户上传图片: {filename}")

async def list_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return
    
    files = sorted(os.listdir(IMAGES_DIR), reverse=True)[:20]  # 最近20张
    
    if not files:
        await update.message.reply_text("📭 还没有上传任何图片")
        return
    
    text = "📷 **最近上传的图片**（最多显示20张）：\n\n"
    for f in files:
        url = f"{PUBLIC_BASE_URL}/images/{f}"
        text += f"• [{f}]({url})\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

# ==================== 记事本功能 ====================
async def show_notes_menu(query):
    notes = get_all_notes()
    
    keyboard = [
        [InlineKeyboardButton("➕ 添加新记事", callback_data="add_note")],
        [InlineKeyboardButton("📋 查看所有记事", callback_data="list_notes")],
    ]
    if notes:
        keyboard.append([InlineKeyboardButton("🗑️ 批量删除", callback_data="delete_notes_menu")])
    keyboard.append([InlineKeyboardButton("🔙 返回主菜单", callback_data="back_main")])
    
    text = f"📝 **记事本** ({len(notes)} 条记录)\n\n请选择操作："
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def add_note_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📝 **添加新记事**\n\n"
        "请先输入记事标题（例如：会议记录）：",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADD_NOTE_TITLE

async def add_note_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['note_title'] = update.message.text.strip()
    await update.message.reply_text(
        "✅ 标题已记录！\n\n"
        "现在请输入记事内容（支持多行）：",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADD_NOTE_CONTENT

async def add_note_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = context.user_data['note_title']
    content = update.message.text.strip()
    
    note_id = add_note(title, content)
    
    await update.message.reply_text(
        f"✅ **记事添加成功！**\n\n"
        f"ID: `{note_id}`\n"
        f"标题: {title}\n\n"
        f"内容预览:\n{content[:100]}{'...' if len(content) > 100 else ''}",
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
    keyboard = []
    
    for note in notes:
        text += f"**ID {note['id']}** | {note['title']}\n"
        text += f"更新: {note['updated_at']}\n\n"
        keyboard.append([
            InlineKeyboardButton(f"✏️ 编辑 #{note['id']}", callback_data=f"note_edit_{note['id']}"),
            InlineKeyboardButton(f"🗑️ 删除 #{note['id']}", callback_data=f"note_delete_{note['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 返回记事本菜单", callback_data="menu_notes")])
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_note_action(query, data):
    if data == "add_note":
        # 启动添加流程（需要发送新消息）
        await query.message.reply_text(
            "请使用 /addnote 命令开始添加记事"
        )
        return
    
    if data == "list_notes":
        await list_notes_from_query(query)
        return
    
    if data.startswith("note_edit_"):
        note_id = int(data.split("_")[2])
        note = get_note(note_id)
        if note:
            context = {"note_id": note_id, "note": note}
            # 简化：直接回复编辑提示
            await query.message.reply_text(
                f"✏️ **编辑记事 #{note_id}**\n\n"
                f"当前标题: {note['title']}\n\n"
                f"请发送新标题（或输入 /cancel 取消）：",
                parse_mode=ParseMode.MARKDOWN
            )
            # 这里可以扩展为 ConversationHandler，但为简化代码，省略完整编辑流程
            # 实际生产可添加 edit_note_title 等状态
        return
    
    if data.startswith("note_delete_"):
        note_id = int(data.split("_")[2])
        delete_note(note_id)
        await query.edit_message_text(f"✅ 已删除记事 #{note_id}")
        return

async def list_notes_from_query(query):
    notes = get_all_notes()
    if not notes:
        await query.edit_message_text("📭 还没有任何记事")
        return
    
    text = "📝 **所有记事本**：\n\n"
    for note in notes:
        text += f"**#{note['id']}** {note['title']}\n"
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

# ==================== 收藏夹功能 ====================
async def show_bookmarks_menu(query):
    bookmarks = get_all_bookmarks()
    
    keyboard = [
        [InlineKeyboardButton("➕ 添加新收藏", callback_data="add_bookmark")],
        [InlineKeyboardButton("📋 查看所有收藏", callback_data="list_bookmarks")],
    ]
    if bookmarks:
        keyboard.append([InlineKeyboardButton("🗑️ 批量删除", callback_data="delete_bookmarks_menu")])
    keyboard.append([InlineKeyboardButton("🔙 返回主菜单", callback_data="back_main")])
    
    text = f"🔖 **网络收藏夹** ({len(bookmarks)} 条记录)\n\n请选择操作："
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def add_bookmark_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔖 **添加新收藏**\n\n"
        "请发送收藏的 URL（例如：https://github.com）：",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADD_BOOKMARK_URL

async def add_bookmark_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("❌ URL 格式不正确，请重新发送以 http:// 或 https:// 开头的链接")
        return ADD_BOOKMARK_URL
    
    context.user_data['bookmark_url'] = url
    await update.message.reply_text(
        "✅ URL 已记录！\n\n"
        "请输入标题（例如：GitHub 官网）：",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADD_BOOKMARK_REMARK  # 复用状态，实际是标题

async def add_bookmark_remark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    url = context.user_data['bookmark_url']
    
    # 这里 remark 留空，用户可后续编辑
    bookmark_id = add_bookmark(title, url, "")
    
    await update.message.reply_text(
        f"✅ **收藏添加成功！**\n\n"
        f"ID: `{bookmark_id}`\n"
        f"标题: {title}\n"
        f"URL: {url}\n\n"
        f"💡 可使用 /editbookmark {bookmark_id} 添加备注",
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
    keyboard = []
    
    for bm in bookmarks:
        text += f"**ID {bm['id']}** | {bm['title']}\n"
        text += f"🔗 {bm['url']}\n"
        if bm['remark']:
            text += f"📝 {bm['remark']}\n"
        text += f"更新: {bm['updated_at']}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(f"✏️ 编辑 #{bm['id']}", callback_data=f"bookmark_edit_{bm['id']}"),
            InlineKeyboardButton(f"🗑️ 删除 #{bm['id']}", callback_data=f"bookmark_delete_{bm['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 返回收藏夹菜单", callback_data="menu_bookmarks")])
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

async def handle_bookmark_action(query, data):
    # 类似 note 的处理，简化实现
    if data.startswith("bookmark_delete_"):
        bm_id = int(data.split("_")[2])
        delete_bookmark(bm_id)
        await query.edit_message_text(f"✅ 已删除收藏 #{bm_id}")
        return
    
    if data.startswith("bookmark_edit_"):
        bm_id = int(data.split("_")[2])
        bm = get_bookmark(bm_id)
        if bm:
            await query.message.reply_text(
                f"✏️ **编辑收藏 #{bm_id}**\n\n"
                f"当前标题: {bm['title']}\n"
                f"URL: {bm['url']}\n"
                f"备注: {bm['remark'] or '无'}\n\n"
                f"请发送新标题（格式：标题|备注）：",
                parse_mode=ParseMode.MARKDOWN
            )
        return

# ==================== 备份功能 ====================
async def show_backup_menu(query):
    keyboard = [
        [InlineKeyboardButton("☁️ 立即备份到 WebDAV", callback_data="do_backup")],
        [InlineKeyboardButton("📤 导出数据（发送 zip）", callback_data="export_data")],
        [InlineKeyboardButton("📥 导入数据（上传 zip）", callback_data="import_data")],
        [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_main")],
    ]
    
    text = (
        "☁️ **备份管理**\n\n"
        f"• WebDAV 自动备份：每 {BACKUP_INTERVAL_HOURS} 小时\n"
        "• 支持完整导出/导入（数据库 + 图片）\n"
        "• 建议定期手动备份重要数据"
    )
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def do_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return
    
    await update.message.reply_text("⏳ 正在创建备份并上传到 WebDAV，请稍候...")
    
    try:
        zip_path = backup_now()
        await update.message.reply_text(
            f"✅ **备份完成！**\n\n"
            f"本地文件：`{os.path.basename(zip_path)}`\n"
            f"已上传到 WebDAV（如果配置正确）",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(f"❌ 备份失败: {str(e)}")

async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return
    
    await update.message.reply_text("⏳ 正在生成导出文件...")
    
    try:
        zip_path = create_backup_zip()
        with open(zip_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(zip_path),
                caption="✅ 数据导出完成！包含数据库和所有图片。"
            )
        os.remove(zip_path)  # 发送后删除临时文件
    except Exception as e:
        await update.message.reply_text(f"❌ 导出失败: {str(e)}")

async def handle_import(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return
    
    if not update.message.document:
        await update.message.reply_text("请上传 .zip 备份文件")
        return
    
    doc = update.message.document
    if not doc.file_name.endswith(".zip"):
        await update.message.reply_text("❌ 只支持 .zip 格式的备份文件")
        return
    
    await update.message.reply_text("⏳ 正在下载并恢复数据...")
    
    try:
        file = await context.bot.get_file(doc.file_id)
        zip_path = os.path.join(IMAGES_DIR, "import_temp.zip")
        await file.download_to_drive(zip_path)
        
        if restore_from_zip(zip_path):
            await update.message.reply_text("✅ **数据导入成功！**\n\nBot 将在下次重启后使用新数据。")
        else:
            await update.message.reply_text("❌ 导入失败，请检查文件是否正确。")
        
        os.remove(zip_path)
    except Exception as e:
        await update.message.reply_text(f"❌ 导入失败: {str(e)}")

# ==================== 定时备份 ====================
from apscheduler.schedulers.background import BackgroundScheduler

def schedule_backup():
    if BACKUP_INTERVAL_HOURS > 0:
        scheduler = BackgroundScheduler()
        scheduler.add_job(backup_now, 'interval', hours=BACKUP_INTERVAL_HOURS)
        scheduler.start()
        logger.info(f"定时备份已启动：每 {BACKUP_INTERVAL_HOURS} 小时")

# ==================== 主程序 ====================
def main():
    # 初始化数据库
    init_db()
    
    # 启动 Flask Web 服务器（后台线程）
    def run_flask():
        flask_app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
    
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask Web 服务器已启动在端口 8080")
    
    # 启动定时备份
    schedule_backup()
    
    # 创建 Bot Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # 命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("images", list_images))
    application.add_handler(CommandHandler("notes", list_notes))
    application.add_handler(CommandHandler("bookmarks", list_bookmarks))
    application.add_handler(CommandHandler("backup", do_backup))
    application.add_handler(CommandHandler("export", export_data))
    
    # 照片处理器
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # 文档导入处理器
    application.add_handler(MessageHandler(filters.Document.ALL, handle_import))
    
    # 记事本 ConversationHandler
    note_conv = ConversationHandler(
        entry_points=[CommandHandler("addnote", add_note_start)],
        states={
            ADD_NOTE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_note_title)],
            ADD_NOTE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_note_content)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )
    application.add_handler(note_conv)
    
    # 收藏夹 ConversationHandler
    bookmark_conv = ConversationHandler(
        entry_points=[CommandHandler("addbookmark", add_bookmark_start)],
        states={
            ADD_BOOKMARK_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_bookmark_url)],
            ADD_BOOKMARK_REMARK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_bookmark_remark)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )
    application.add_handler(bookmark_conv)
    
    # 按钮回调
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # 启动 Bot（轮询模式）
    logger.info("Bot 启动中...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()