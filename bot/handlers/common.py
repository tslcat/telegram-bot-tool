from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from bot.handlers.tool1 import enter_notebook as enter_tool1
from bot.handlers.tool2 import enter_imagebed as enter_tool2
from bot.handlers.tool3 import enter_backup as enter_tool3

router = Router(name="common")

# ==================== 主菜单键盘（底部常驻） ====================
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📓 笔记本"),
            KeyboardButton(text="🖼️ 图床")
        ],
        [
            KeyboardButton(text="🗄️ 备份"),
            KeyboardButton(text="❓ 帮助")
        ]
    ],
    resize_keyboard=True,
    persistent=True,
    input_field_placeholder="请选择功能或输入命令"
)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 欢迎使用 <b>Telegram Bot Tool</b>！\n\n"
        "主菜单已固定在底部，点击按钮即可使用对应功能。",
        reply_markup=main_menu
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

# ==================== 底部主菜单按钮处理 ====================
@router.message(F.text == "📓 笔记本")
async def handle_notebook_button(message: Message, state: FSMContext):
    await enter_tool1(message, state)

@router.message(F.text == "🖼️ 图床")
async def handle_imagebed_button(message: Message, state: FSMContext):
    await enter_tool2(message, state)

@router.message(F.text == "🗄️ 备份")
async def handle_backup_button(message: Message, state: FSMContext):
    await enter_tool3(message, state)

@router.message(F.text == "❓ 帮助")
async def handle_help_button(message: Message):
    await cmd_help(message)