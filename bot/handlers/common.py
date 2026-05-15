from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

router = Router(name="common")

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 欢迎使用 <b>Telegram Bot Tool</b>！\n\n"
        "这是一个模块化的多工具 Bot，包含以下功能：\n\n"
        "📓 <b>/tool1</b> - 笔记本功能（添加/查看/删除笔记）\n"
        "🖼️ <b>/tool2</b> - 图床功能（上传图片获取多格式链接）\n"
        "🗄️ <b>/tool3</b> - 备份功能（导出/导入/WebDAV备份）\n\n"
        "使用 <b>/help</b> 查看详细帮助"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>帮助菜单</b>\n\n"
        "• <b>/tool1</b> - 笔记本功能\n"
        "• <b>/tool2</b> - 图床功能（需配置 SMMS_TOKEN）\n"
        "• <b>/tool3</b> - 备份功能（需配置 WebDAV）\n\n"
        "每个工具都有独立的菜单，操作简单直观。"
    )