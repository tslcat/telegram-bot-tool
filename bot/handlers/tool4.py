from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os

from bot.database import add_proxy, get_user_proxies, delete_proxy_by_id

router = Router(name="tool4")

class ProxyStates(StatesGroup):
    choosing_action = State()
    waiting_domain = State()
    waiting_delete_number = State()

async def show_proxy_menu(target: Message | CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ 添加反向代理", callback_data="proxy_add")],
        [InlineKeyboardButton(text="📋 查看全部代理", callback_data="proxy_view")],
        [InlineKeyboardButton(text="📊 流量统计", callback_data="proxy_stats")],
        [InlineKeyboardButton(text="🔙 返回主菜单", callback_data="proxy_back")]
    ])
    text = "🌐 <b>反向代理管理</b>\n请选择操作："
    
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ProxyStates.choosing_action)

@router.message(Command("tool4"))
async def enter_proxy(message: Message, state: FSMContext):
    await state.clear()
    await show_proxy_menu(message, state)

# 添加反向代理
@router.callback_query(F.data == "proxy_add", StateFilter(ProxyStates.choosing_action))
async def add_proxy_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "➕ <b>添加反向代理</b>\n\n"
        "请输入要代理的域名（例如：example.com）\n"
        "后续可扩展为输入目标地址"
    )
    await state.set_state(ProxyStates.waiting_domain)
    await callback.answer()

@router.message(ProxyStates.waiting_domain)
async def save_proxy(message: Message, state: FSMContext):
    domain = message.text.strip()
    if not domain:
        await message.answer("⚠️ 域名不能为空，请重新输入：")
        return

    target = "http://127.0.0.1:8080"  # 默认示例，可后续扩展

    try:
        await add_proxy(message.from_user.id, domain, target)
        await message.answer(
            f"✅ <b>反向代理添加成功！</b>\n\n"
            f"域名：<code>{domain}</code>\n"
            f"目标：<code>{target}</code>\n\n"
            f"请在 Caddy 中配置对应路由后重载。"
        )
    except Exception as e:
        await message.answer(f"❌ 添加失败：{e}")

    await show_proxy_menu(message, state)

# 查看全部代理 + 删除
@router.callback_query(F.data == "proxy_view", StateFilter(ProxyStates.choosing_action))
async def view_proxies(callback: CallbackQuery, state: FSMContext):
    proxies = await get_user_proxies(callback.from_user.id)
    if not proxies:
        await callback.message.edit_text("📭 你还没有添加任何反向代理。")
        await show_proxy_menu(callback.message, state)
        await callback.answer()
        return

    text = "📋 <b>已添加的反向代理</b>（按时间倒序）\n\n"
    for idx, p in enumerate(proxies, 1):
        text += f"<b>{idx}.</b> {p['domain']} → {p['target']}\n   添加时间：{p['created_at']}\n\n"

    text += "━━━━━━━━━━━━━━\n"
    text += "💡 直接回复 <b>序号</b> 删除对应代理\n回复 <b>0</b> 返回菜单"

    await callback.message.edit_text(text, parse_mode="HTML")
    await state.update_data(proxies_list=proxies)
    await state.set_state(ProxyStates.waiting_delete_number)
    await callback.answer()

@router.message(ProxyStates.waiting_delete_number)
async def handle_delete_proxy(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "0":
        await show_proxy_menu(message, state)
        return
    try:
        num = int(text)
    except ValueError:
        await message.answer("⚠️ 请输入有效的序号或 0 返回菜单")
        return

    data = await state.get_data()
    proxies = data.get("proxies_list", [])
    if num < 1 or num > len(proxies):
        await message.answer(f"⚠️ 序号超出范围，请输入 1~{len(proxies)}")
        return

    proxy = proxies[num-1]
    success = await delete_proxy_by_id(proxy["id"], message.from_user.id)
    if success:
        await message.answer(f"✅ 已删除第 {num} 个代理：{proxy['domain']}")
    else:
        await message.answer("❌ 删除失败")
    await show_proxy_menu(message, state)

# 流量统计（占位）
@router.callback_query(F.data == "proxy_stats", StateFilter(ProxyStates.choosing_action))
async def proxy_stats(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📊 <b>流量统计</b>\n\n"
        "当前版本暂未接入 Caddy 流量统计。\n"
        "可后续接入 Prometheus + Caddy metrics 实现实时流量监控。",
        parse_mode="HTML"
    )
    await show_proxy_menu(callback.message, state)
    await callback.answer()

@router.callback_query(F.data == "proxy_back")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🔙 已返回主菜单\n使用 /tool4 再次进入反向代理管理")
    await callback.answer()