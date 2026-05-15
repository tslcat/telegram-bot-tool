from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
import os

from bot.database import add_image_record

router = Router(name="tool2")

SMMS_TOKEN = os.getenv("SMMS_TOKEN")
SMMS_UPLOAD_URL = "https://sm.ms/api/v2/upload"

class ImageBedStates(StatesGroup):
    choosing_action = State()
    waiting_for_image = State()

async def show_imagebed_menu(target: Message | CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ 添加图片", callback_data="imgbed_add")],
        [InlineKeyboardButton(text="🔙 返回主菜单", callback_data="imgbed_back")]
    ])
    text = "🖼️ <b>图床菜单</b>\n请选择操作："
    
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
        await target.answer()
    else:
        await target.answer(text, reply_markup=keyboard)
    await state.set_state(ImageBedStates.choosing_action)

@router.message(Command("tool2"))
async def enter_imagebed(message: Message, state: FSMContext):
    await state.clear()
    await show_imagebed_menu(message, state)

@router.callback_query(F.data == "imgbed_add", StateFilter(ImageBedStates.choosing_action))
async def add_image_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📤 请直接发送图片（照片或文件）")
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

    await message.answer("⏳ 正在上传到图床...")

    headers = {}
    if SMMS_TOKEN:
        headers["Authorization"] = f"Bearer {SMMS_TOKEN}"

    form = aiohttp.FormData()
    form.add_field("smfile", file_bytes, filename=filename, content_type="image/jpeg")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(SMMS_UPLOAD_URL, data=form, headers=headers) as resp:
                result = await resp.json()

        if result.get("success"):
            data = result.get("data", {})
            url = data.get("url", "")
            
            # 保存记录到数据库
            await add_image_record(message.from_user.id, url, filename)

            text = (
                "✅ <b>上传成功！</b>\n\n"
                f"**直链 (URL)**:\n`{url}`\n\n"
                f"**HTML**:\n`<img src=\"{url}\" />`\n\n"
                f"**BBCode**:\n`[img]{url}[/img]`\n\n"
                f"**Markdown**:\n`![图片]({url})`"
            )
            await message.answer(text, parse_mode="Markdown")
        else:
            await message.answer(f"❌ 上传失败：{result.get('message', '未知错误')}")
    except Exception as e:
        await message.answer(f"❌ 上传出错：{e}")

    await show_imagebed_menu(message, state)

@router.callback_query(F.data == "imgbed_back")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🔙 已返回主菜单\n使用 /tool2 再次进入图床")
    await callback.answer()