from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json
from datetime import datetime

from bot.database import (
    get_all_notes, get_all_images, get_all_proxies,
    clear_all_notes, bulk_insert_notes,
    clear_all_images, bulk_insert_images,
    clear_all_proxies, bulk_insert_proxies
)

router = Router(name="tool3")


class BackupStates(StatesGroup):
    choosing_action = State()
    waiting_for_import_file = State()

async def show_backup_menu(target: Message | CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 导出文件", callback_data="backup_export")],
        [InlineKeyboardButton(text="📥 导入文件", callback_data="backup_import")],
        [InlineKeyboardButton(text="🔙 返回主菜单", callback_data="backup_back")]
    ])
    text = "🗄️ <b>备份菜单</b>\n请选择操作："
    
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(BackupStates.choosing_action)

@router.message(Command("tool3"))
async def enter_backup(message: Message, state: FSMContext):
    await state.clear()
    await show_backup_menu(message, state)

@router.callback_query(F.data == "backup_export", StateFilter(BackupStates.choosing_action))
async def export_backup(callback: CallbackQuery, state: FSMContext):
    notes = await get_all_notes()
    images = await get_all_images()
    proxies = await get_all_proxies()

    backup_data = {
        "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "notes": notes,
        "images": images,
        "proxies": proxies
    }

    json_str = json.dumps(backup_data, ensure_ascii=False, indent=2)
    filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    await callback.message.answer_document(
        BufferedInputFile(json_str.encode("utf-8"), filename=filename),
        caption="✅ 备份文件已生成，请下载保存！\n包含笔记、图床、反向代理数据"
    )
    await show_backup_menu(callback.message, state)
    await callback.answer()

@router.callback_query(F.data == "backup_import", StateFilter(BackupStates.choosing_action))
async def import_backup_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📥 请直接上传之前导出的 `.json` 备份文件")
    await state.set_state(BackupStates.waiting_for_import_file)
    await callback.answer()

@router.message(StateFilter(BackupStates.waiting_for_import_file), F.document)
async def handle_import_file(message: Message, state: FSMContext, bot: Bot):
    if not message.document.file_name.endswith(".json"):
        await message.answer("⚠️ 请上传 .json 格式的备份文件")
        return

    try:
        file = await bot.get_file(message.document.file_id)
        file_bytes = await bot.download_file(file.file_path)
        data = json.loads(file_bytes.getvalue().decode("utf-8"))

        await clear_all_notes()
        await clear_all_images()
        await clear_all_proxies()

        if "notes" in data:
            await bulk_insert_notes(data["notes"])
        if "images" in data:
            await bulk_insert_images(data["images"])
        if "proxies" in data:
            await bulk_insert_proxies(data["proxies"])

        await message.answer("✅ 备份恢复成功！数据已导入。")
    except Exception as e:
        await message.answer(f"❌ 导入失败：{e}")

    await show_backup_menu(message, state)

@router.callback_query(F.data == "backup_back")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🔙 已返回主菜单\n使用 /tool3 再次进入备份功能")
    await callback.answer()