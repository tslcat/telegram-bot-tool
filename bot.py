#!/usr/bin/env python3
"""
Telegram 个人工具箱 Bot - 生产稳定版 v2.0
已修复 ConnectTimeout 问题 + 增强异常处理
"""

import logging
import os
import uuid
from threading import Thread
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from telegram.constants import ParseMode
from telegram.error import TimedOut, NetworkError
from telegram.request import HTTPXRequest

# ==================== 配置区 ====================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OWNER_CHAT_ID = int(os.getenv("OWNER_CHAT_ID", "0"))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8080")
IMAGES_DIR = os.getenv("IMAGES_DIR", "/app/images")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 工具函数 ====================
async def safe_answer(query, text: str = None):
    """安全回复 callback query，防止网络超时导致崩溃"""
    try:
        await query.answer(text)
    except (TimedOut, NetworkError) as e:
        logger.warning(f"⚠️ 无法回复按钮点击（网络问题）: {e}")
    except Exception as e:
        logger.error(f"❌ 回复按钮时发生未知错误: {e}")

async def safe_edit_message(query, text: str, reply_markup=None, parse_mode=None):
    """安全编辑消息"""
    try:
        await query.edit_message_text(
            text, 
            reply_markup=reply_markup, 
            parse_mode=parse_mode
        )
    except (TimedOut, NetworkError) as e:
        logger.warning(f"⚠️ 编辑消息失败（网络问题）: {e}")
    except Exception as e:
        logger.error(f"❌ 编辑消息时发生错误: {e}")

# ==================== 菜单 ====================
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📷 图床管理", callback_data="menu_images")],
        [InlineKeyboardButton("📝 记事本", callback_data="menu_notes")],
        [InlineKeyboardButton("🔖 收藏夹", callback_data="menu_bookmarks")],
        [InlineKeyboardButton("☁️ 备份管理", callback_data="menu_backup")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== 处理器 ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_CHAT_ID:
        await update.message.reply_text("⛔ 仅限主人使用")
        return
    await update.message.reply_text(
        "👋 **欢迎使用 Telegram 个人工具箱 v2.0**！\n请选择功能：",
        reply_markup=get_main_menu(),
        parse_mode=ParseMode.MARKDOWN
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # 关键修复：先安全回复按钮，避免超时崩溃
    await safe_answer(query)
    
    if query.from_user.id != OWNER_CHAT_ID:
        return
    
    data = query.data

    if data == "menu_images":
        await safe_edit_message(
            query, 
            "📷 **图床管理**\n直接发送图片即可上传", 
            reply_markup=get_main_menu()
        )
    elif data == "menu_notes":
        # 这里可以接你的数据库逻辑
        await safe_edit_message(
            query, 
            "📝 **记事本**\n功能开发中...", 
            reply_markup=get_main_menu()
        )
    elif data == "menu_bookmarks":
        await safe_edit_message(
            query, 
            "🔖 **收藏夹**\n功能开发中...", 
            reply_markup=get_main_menu()
        )
    elif data == "menu_backup":
        keyboard = [
            [InlineKeyboardButton("☁️ 立即备份", callback_data="do_backup")],
            [InlineKeyboardButton("📤 导出数据", callback_data="export_data")],
            [InlineKeyboardButton("📥 导入数据", callback_data="import_data")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_main")],
        ]
        await safe_edit_message(
            query, 
            "☁️ **备份管理**\n请选择操作：", 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    elif data == "back_main":
        await safe_edit_message(
            query, 
            "👋 **欢迎使用 Telegram 个人工具箱**！\n请选择功能：", 
            reply_markup=get_main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
    elif data == "do_backup":
        await safe_edit_message(query, "☁️ 正在执行备份...")
        # TODO: 接入真实 WebDAV 逻辑
        await query.message.reply_text("✅ 备份成功！（演示模式）")
    elif data == "export_data":
        await safe_edit_message(query, "📤 正在导出数据...")
        await query.message.reply_text("✅ 导出完成！（演示模式）")
    elif data == "import_data":
        await safe_edit_message(query, "📥 请上传 .zip 备份文件")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 这里保留你原来的记事本/收藏夹逻辑
    text = update.message.text.strip()
    if context.user_data.get('adding_note'):
        # ... 你的 add_note 逻辑
        await update.message.reply_text("✅ 记事添加成功！")
        context.user_data.clear()
    elif context.user_data.get('adding_bookmark'):
        # ... 你的 add_bookmark 逻辑
        await update.message.reply_text("✅ 收藏添加成功！")
        context.user_data.clear()

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_CHAT_ID:
        return
    # ... 你的图片上传逻辑
    await update.message.reply_text("✅ 图片上传成功！")

# ==================== 主程序 ====================
def main():
    init_db()  # 你的数据库初始化

    # 启动 Flask（图床服务）
    def run_flask():
        flask_app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
    Thread(target=run_flask, daemon=True).start()

    # ========== 关键网络配置 ==========
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
        # 如果你在中国大陆或需要代理，取消下面注释并填入你的代理地址：
        # proxy_url="http://127.0.0.1:7890",   # Clash/V2Ray 示例
    )

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .request(request)
        .build()
    )

    # 注册处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🚀 Bot 已启动（稳定版 v2.0）")
    application.run_polling()

if __name__ == "__main__":
    main()