from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.database import add_note, get_user_notes, delete_note_by_id

router = Router(name="tool1")

class NoteStates(StatesGroup):
    choosing_action = State()
    waiting_note_content = State()
    waiting_delete_number = State()

async def show_notebook_menu(target: Message | CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ 添加新笔记", callback_data="note_add")],
        [InlineKeyboardButton(text="📋 查看所有笔记", callback_data="note_view")],
        [InlineKeyboardButton(text="🔙 返回主菜单", callback_data="note_back")]
    ])
    text = "📓 <b>笔记本菜单</b>\n请选择操作："
    
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
        await target.answer()
    else:
        await target.answer(text, reply_markup=keyboard)
    await state.set_state(NoteStates.choosing_action)

@router.message(Command("tool1"))
async def enter_notebook(message: Message, state: FSMContext):
    await state.clear()
    await show_notebook_menu(message, state)

@router.callback_query(F.data == "note_add", StateFilter(NoteStates.choosing_action))
async def add_note_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✍️ 请直接输入你要保存的笔记内容：")
    await state.set_state(NoteStates.waiting_note_content)
    await callback.answer()

@router.message(NoteStates.waiting_note_content)
async def save_new_note(message: Message, state: FSMContext):
    content = message.text.strip()
    if not content:
        await message.answer("⚠️ 笔记内容不能为空，请重新输入：")
        return
    try:
        await add_note(message.from_user.id, content)
        await message.answer("✅ <b>笔记保存成功！</b>")
    except Exception as e:
        await message.answer(f"❌ 保存失败：{e}")
    await show_notebook_menu(message, state)

@router.callback_query(F.data == "note_view", StateFilter(NoteStates.choosing_action))
async def view_notes(callback: CallbackQuery, state: FSMContext):
    notes = await get_user_notes(callback.from_user.id)
    if not notes:
        await callback.message.edit_text("📭 你还没有任何笔记。")
        await show_notebook_menu(callback.message, state)
        await callback.answer()
        return

    text = "📋 <b>你的所有笔记</b>（按时间倒序）\n\n"
    for idx, note in enumerate(notes, 1):
        text += f"<b>{idx}.</b> [{note['created_at']}]\n{note['content']}\n\n"

    text += "━━━━━━━━━━━━━━\n"
    text += "💡 直接回复 <b>序号</b> 删除对应笔记\n回复 <b>0</b> 返回菜单"

    await callback.message.edit_text(text)
    await state.update_data(notes_list=notes)
    await state.set_state(NoteStates.waiting_delete_number)
    await callback.answer()

@router.message(NoteStates.waiting_delete_number)
async def handle_delete_input(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "0":
        await show_notebook_menu(message, state)
        return
    try:
        num = int(text)
    except ValueError:
        await message.answer("⚠️ 请输入有效的序号或 0 返回菜单")
        return

    data = await state.get_data()
    notes = data.get("notes_list", [])
    if num < 1 or num > len(notes):
        await message.answer(f"⚠️ 序号超出范围，请输入 1~{len(notes)}")
        return

    note = notes[num-1]
    success = await delete_note_by_id(note["id"], message.from_user.id)
    if success:
        await message.answer(f"✅ 已删除第 {num} 条笔记")
    else:
        await message.answer("❌ 删除失败")
    await show_notebook_menu(message, state)

@router.callback_query(F.data == "note_back")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🔙 已返回主菜单\n使用 /tool1 再次进入笔记本")
    await callback.answer()