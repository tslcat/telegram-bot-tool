#!/usr/bin/env python3
"""
Telegram 个人工具箱 Bot - 优化版
支持：图床（多格式）、记事本、WebDAV 备份
"""

import logging
import os
import uuid
from datetime import datetime
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from telegram.constants import ParseMode
from telegram.error import TimedOut

from config import (
    TELEGRAM_TOKEN, OWNER_CHAT_ID, PUBLIC_BASE_URL,
    IMAGES_DIR, BACKUP_INTERVAL_HOURS
)
from database import (
    init_db, add_note, get_all_notes, get_note, update_note, delete_note
)
from webdav_backup import backup_now, restore_from_zip, create_backup_zip
from web import app as flask_app

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ADD_NOTE_TITLE, ADD_NOTE_CONTENT = range(2)


# ==================== 全局错误处理 ====================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """全局错误处理器，防止 Bot 因单次请求崩溃"""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)

    if isinstance(context.error, TimedOut):
        logger.warning("Telegram API 请求超时，已忽略")
        return

    # 可选：通知主人
    try:
        if update and hasattr(update, "effective_user"):
            await context.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=f"⚠️ Bot 发生错误：{str(context.error)[:150]}"
            )
    except Exception:
        pass


async def check_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if update.effective_user.id != OWNER_CHAT_ID:
        await update.message.reply_text("⛔ 仅限主人使用")
        return False
    return True


# ==================== 主菜单 ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return

    keyboard = [
        [InlineKeyboardButton("📷 图床管理", callback_data="menu_images")],
        [InlineKeyboardButton("📝 记事本", callback_data="menu_notes")],
        [InlineKeyboardButton("☁️ 备份管理", callback_data="menu_backup")],
    ]
    await update.message.reply_text(
        "👋 **欢迎使用 Telegram 个人工具箱**！\n请选择功能：",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass  # 防止 answer 超时导致崩溃

    if query.from_user.id != OWNER_CHAT_ID:
        return

    data = query.data

    if data == "menu_images":
        await show_images_menu(query)
    elif data == "menu_notes":
        await show_notes_menu(query)
    elif data == "menu_backup":
        await show_backup_menu(query)
    elif data == "delete_notes_menu":
        await show_delete_notes_menu(query)
    elif data.startswith("note_"):
        await handle_note_action(query, data)
    elif data == "back_main":
        await show_main_menu(query)


async def show_main_menu(query):
    keyboard = [
        [InlineKeyboardButton("📷 图床管理", callback_data="menu_images")],
        [InlineKeyboardButton("📝 记事本", callback_data="menu_notes")],
        [InlineKeyboardButton("☁️ 备份管理", callback_data="menu_backup")],
    ]
    await query.edit_message_text(
        "👋 **欢迎使用 Telegram 个人工具箱**！\n请选择功能：",
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
        "• 直接发送图片自动上传\n"
        "• 支持 URL、HTML、BBCode、Markdown 格式",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(IMAGES_DIR, filename)
    await file.download_to_drive(filepath)

    image_url = f"{PUBLIC_BASE_URL}/images/{filename}"
    html = f'<img src="{image_url}" alt="image" />'
    bbcode = f'[img]{image_url}[/img]'
    markdown = f'![image]({image_url})'

    await update.message.reply_text(
        f"✅ **上传成功！**\n\n"
        f"**URL:** `{image_url}`\n"
        f"**HTML:** `{html}`\n"
        f"**BBCode:** `{bbcode}`\n"
        f"**Markdown:** `{markdown}`",
        parse_mode=ParseMode.MARKDOWN
    )


async def list_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return

    files = sorted(os.listdir(IMAGES_DIR), reverse=True)[:20]
    if not files:
        await update.message.reply_text("📭 还没有上传图片")
        return

    text = "📷 **最近上传的图片**：\n\n"
    for f in files:
        text += f"• [{f}]({PUBLIC_BASE_URL}/images/{f})\n"
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

    await query.edit_message_text(
        f"📝 **记事本** ({len(notes)} 条)\n请选择操作：",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def add_note_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return ConversationHandler.END
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
    await update.message.reply_text(f"✅ 添加成功！ID: {note_id}")
    context.user_data.clear()


async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return

    notes = get_all_notes()
    if not notes:
        await update.message.reply_text("📭 还没有记事")
        return

    context.user_data['current_note_ids'] = [note['id'] for note in notes]

    text = "📝 **所有记事本**：\n\n"
    for i, note in enumerate(notes, 1):
        text += f"{i}. {note['title']}\n   更新: {note['updated_at']}\n\n"

    text += "💡 输入 `0` 进入删除模式，然后输入序号删除"

    keyboard = [[InlineKeyboardButton("🗑️ 批量删除", callback_data="delete_notes_menu")]]
    keyboard.append([InlineKeyboardButton("🔙 返回", callback_data="menu_notes")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)


async def show_delete_notes_menu(query):
    notes = get_all_notes()
    if not notes:
        await query.edit_message_text("📭 没有可删除的记事", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 返回", callback_data="menu_notes")]]))
        return

    text = "🗑️ **点击序号删除**：\n\n"
    keyboard = []
    for i, note in enumerate(notes, 1):
        text += f"{i}. {note['title']}\n"
        keyboard.append([InlineKeyboardButton(f"❌ 删除 {i}", callback_data=f"note_delete_{note['id']}")])

    keyboard.append([InlineKeyboardButton("🔙 返回", callback_data="menu_notes")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)


async def handle_note_action(query, data):
    if data.startswith("note_delete_"):
        note_id = int(data.split("_")[2])
        delete_note(note_id)
        await query.edit_message_text(f"✅ 已删除记事 #{note_id}")


# ==================== 备份功能 ====================
async def show_backup_menu(query):
    keyboard = [
        [InlineKeyboardButton("☁️ 立即备份到 WebDAV", callback_data="do_backup")],
        [InlineKeyboardButton("📤 导出数据", callback_data="export_data")],
        [InlineKeyboardButton("📥 导入数据", callback_data="import_data")],
        [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_main")],
    ]
    text = f"☁️ **备份管理**\n默认每 {BACKUP_INTERVAL_HOURS} 小时自动备份到 WebDAV"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)


async def do_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return
    await update.message.reply_text("⏳ 正在备份中...")
    try:
        zip_path = backup_now()
        await update.message.reply_text("✅ 备份完成！已上传到 WebDAV")
    except Exception as e:
        await update.message.reply_text(f"❌ 备份失败: {e}")


async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return
    try:
        zip_path = create_backup_zip()
        with open(zip_path, "rb") as f:
            await update.message.reply_document(document=f, filename=os.path.basename(zip_path))
        os.remove(zip_path)
    except Exception as e:
        await update.message.reply_text(f"❌ 导出失败: {e}")


async def handle_import(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update, context):
        return

    if not update.message.document or not update.message.document.file_name.endswith(".zip"):
        await update.message.reply_text("请上传 .zip 备份文件")
        return

    await update.message.reply_text("⏳ 正在导入数据...")

    try:
        file = await context.bot.get_file(update.message.document.file_id)
        zip_path = os.path.join(IMAGES_DIR, "import_temp.zip")
        await file.download_to_drive(zip_path)

        if restore_from_zip(zip_path):
            await update.message.reply_text("✅ **导入成功！** Bot 将在下次重启后使用新数据。")
        else:
            await update.message.reply_text("❌ 导入失败")

        os.remove(zip_path)
    except Exception as e:
        await update.message.reply_text(f"❌ 导入失败: {e}")


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
    init_db()

    def run_flask():
        flask_app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False, threaded=True)

    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask Web 服务器已启动")

    schedule_backup()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 注册全局错误处理器
    application.add_error_handler(error_handler)

    # 注册处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("notes", list_notes))
    application.add_handler(CommandHandler("backup", do_backup))
    application.add_handler(CommandHandler("export", export_data))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_import))

    note_conv = ConversationHandler(
        entry_points=[CommandHandler("addnote", add_note_start)],
        states={
            ADD_NOTE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_note_title)],
            ADD_NOTE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_note_content)],
        },
        fallbacks=[],
    )
    application.add_handler(note_conv)
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot 启动中...")

    # 优化后的 polling 配置
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,   # 丢弃启动时积压的更新
        poll_interval=1.0,
        timeout=20,
        read_timeout=30,
    )


if __name__ == "__main__":
    main()