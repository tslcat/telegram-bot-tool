from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from bot.handlers.tool1 import enter_notebook as enter_tool1
from bot.handlers.tool2 import enter_imagebed as enter_tool2
from bot.handlers.tool3 import enter_backup as enter_tool3
from bot.handlers.tool4 import enter_proxy as enter_tool4

router = Router(name="common")

# ==================== 主菜单键盘（底部常驻） ====================
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📓 笔记本"),
            KeyboardButton(text="🖼️ 图床")
        ],
        [
            KeyboardButton(text="🌐 反向代理"),
            KeyboardButton(text="🗄️ 备份")
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
        reply_markup=main_menu,
        parse_mode="HTML"
    )

# ==================== 底部主菜单按钮处理 ====================
@router.message(F.text == "📓 笔记本")
async def handle_notebook_button(message: Message, state: FSMContext):
    await enter_tool1(message, state)

@router.message(F.text == "🖼️ 图床")
async def handle_imagebed_button(message: Message, state: FSMContext):
    await enter_tool2(message, state)

@router.message(F.text == "🌐 反向代理")
async def handle_proxy_button(message: Message, state: FSMContext):
    await enter_tool4(message, state)

@router.message(F.text == "🗄️ 备份")
async def handle_backup_button(message: Message, state: FSMContext):
    await enter_tool3(message, state)