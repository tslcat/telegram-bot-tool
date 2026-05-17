from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
import uuid
from datetime import datetime

from bot.database import add_image_record

router = Router(name="tool2")

# 用户配置的图片访问域名（例如：https://img.yourdomain.com/images）
# 如果不配置，则回退到 Telegram 直链
IMAGE_DOMAIN = os.getenv("IMAGE_DOMAIN", "").rstrip("/")


class ImageBedStates(StatesGroup):
    choosing_action = State()
    waiting_for_image = State()


async def show_imagebed_menu(target: Message | CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ 添加图片", callback_data="imgbed_add")],
        [InlineKeyboardButton(text="🔙 返回主菜单", callback_data="imgbed_back")]
    ])
    text = "🖼️ <b>图床菜单</b>\n（支持配置自己的域名生成链接）\n请选择操作："
    
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ImageBedStates.choosing_action)


@router.message(Command("tool2"))
async def enter_imagebed(message: Message, state: FSMContext):
    await state.clear()
    await show_imagebed_menu(message, state)


@router.callback_query(F.data == "imgbed_add", StateFilter(ImageBedStates.choosing_action))
async def add_image_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📤 请直接发送图片（照片或文件）\n\n"
        "• 已配置 IMAGE_DOMAIN → 使用你的域名生成链接\n"
        "• 未配置 → 回退使用 Telegram 直链"
    )
    await state.set_state(ImageBedStates.waiting_for_image)
    await callback.answer()


@router.message(StateFilter(ImageBedStates.waiting_for_image), F.photo | F.document)
async def handle_image_upload(message: Message, state: FSMContext, bot: Bot):
    if message.photo:
        file_id = message.photo[-1].file_id
        filename = "photo.jpg"
    elif message.document:
        file_id = message.document.file_id
        filename = message.document.file_name or "file.jpg"
    else:
        await message.answer("⚠️ 请发送图片")
        return

    try:
        file_info = await bot.get_file(file_id)
        file_bytes_io = await bot.download_file(file_info.file_path)
        file_bytes = file_bytes_io.getvalue()
    except Exception as e:
        await message.answer(f"❌ 下载失败：{e}")
        await show_imagebed_menu(message, state)
        return

    await message.answer("⏳ 正在处理图片...")

    try:
        # 创建图片存储目录
        os.makedirs("data/images", exist_ok=True)

        # 生成唯一文件名
        ext = os.path.splitext(filename)[1] or ".jpg"
        new_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
        save_path = os.path.join("data/images", new_filename)

        # 保存图片到本地
        with open(save_path, "wb") as f:
            f.write(file_bytes)

        # 根据是否配置了 IMAGE_DOMAIN 生成链接
        if IMAGE_DOMAIN:
            url = f"{IMAGE_DOMAIN}/{new_filename}"
            storage_info = "使用你配置的域名"
        else:
            # 没有配置域名时，回退到 Telegram 直链
            sent_message = await bot.send_photo(
                chat_id=message.chat.id,
                photo=BufferedInputFile(file_bytes, filename=filename),
            )
            new_file = await bot.get_file(sent_message.photo[-1].file_id)
            url = f"https://api.telegram.org/file/bot{bot.token}/{new_file.file_path}"
            storage_info = "使用 Telegram 存储（未配置 IMAGE_DOMAIN）"

        # 保存记录到数据库
        await add_image_record(message.from_user.id, url, new_filename)

        text = (
            f"✅ <b>上传成功！</b>（{storage_info}）\n\n"
            f"<b>直链 (URL)</b>:\n<code>{url}</code>\n\n"
            f"<b>HTML</b>:\n<code>&lt;img src=\"{url}\" /&gt;</code>\n\n"
            f"<b>BBCode</b>:\n<code>[img]{url}[/img]</code>\n\n"
            f"<b>Markdown</b>:\n<code>![图片]({url})</code>"
        )
        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ 上传失败：{e}")

    await show_imagebed_menu(message, state)


@router.callback_query(F.data == "imgbed_back")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🔙 已返回主菜单\n使用 /tool2 再次进入图床", parse_mode="HTML")
    await callback.answer()