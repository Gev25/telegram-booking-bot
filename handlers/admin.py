import logging
import functools
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest  # <-- Добавили импорт ошибки

import database as db
from config import ADMIN_IDS, SERVICES
from keyboards import admin_menu_kb, admin_booking_kb
from states import AdminBroadcast

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ──────────────── GUARD ────────────────

def admin_only(func):
    @functools.wraps(func)
    async def wrapper(message_or_cb, *args, **kwargs):
        # Достаем ID пользователя
        uid = message_or_cb.from_user.id
        
        if not is_admin(uid):
            # Проверяем, это сообщение или колбэк, чтобы ответить правильно
            if isinstance(message_or_cb, Message):
                await message_or_cb.answer("⛔️ Нет доступа")
            elif isinstance(message_or_cb, CallbackQuery):
                await message_or_cb.answer("⛔️ Нет доступа", show_alert=True)
            return
        
        # Вызываем оригинальную функцию
        return await func(message_or_cb, *args, **kwargs)
    return wrapper

# ──────────────── ADMIN COMMANDS ────────────────

@router.message(Command("admin"))
@admin_only
async def admin_panel(message: Message, **kwargs):
    await message.answer(
        "🔐 <b>Панель администратора</b>",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:stats")
@admin_only
async def admin_stats(callback: CallbackQuery, **kwargs):
    stats = await db.get_stats()
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"📋 Всего записей: {stats['total_bookings']}\n"
        f"⏳ Ожидают: {stats['pending']}\n"
        f"✅ Подтверждено: {stats['confirmed']}\n"
        f"💚 Оплачено: {stats['paid']}"
    )
    await callback.message.edit_text(text, reply_markup=admin_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "admin:all_bookings")
@admin_only
async def admin_all_bookings(callback: CallbackQuery, **kwargs):
    bookings = await db.get_all_bookings()
    if not bookings:
        await callback.answer("Записей нет", show_alert=True)
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for b in bookings[:20]:
        svc = SERVICES.get(b["service_key"], {"name": "?"})
        status = {"pending": "⏳", "confirmed": "✅", "cancelled": "❌", "done": "🏁"}.get(b["status"], "?")
        # Получаем ID (совместимость с MongoDB '_id' и SQLite 'id')
        b_id = str(b.get("_id", b.get("id")))
        
        builder.button(
            text=f"{status} {b['date']} {b['time']} — {b['full_name'][:15]}",
            callback_data=f"admin_view:{b_id}"
        )
    builder.button(text="⬅️ Назад", callback_data="admin:menu")
    builder.adjust(1)

    await callback.message.edit_text(
        f"📋 <b>Все записи ({len(bookings)})</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:pending_bookings")
@admin_only
async def admin_pending_bookings(callback: CallbackQuery, **kwargs):
    bookings = await db.get_all_bookings(status="pending")
    if not bookings:
        await callback.answer("Нет ожидающих записей", show_alert=True)
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for b in bookings:
        b_id = str(b.get("_id", b.get("id")))
        builder.button(
            text=f"⏳ {b['date']} {b['time']} — {b['full_name'][:15]}",
            callback_data=f"admin_view:{b_id}"
        )
    builder.button(text="⬅️ Назад", callback_data="admin:menu")
    builder.adjust(1)

    await callback.message.edit_text(
        f"⏳ <b>Ожидают подтверждения ({len(bookings)})</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:menu")
@admin_only
async def admin_menu_cb(callback: CallbackQuery, **kwargs):
    try:
        await callback.message.edit_text(
            "🔐 <b>Панель администратора</b>",
            reply_markup=admin_menu_kb(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback.answer() # Если меню уже открыто, просто гасим загрузку


@router.callback_query(F.data.startswith("admin_view:"))
@admin_only
async def admin_view_booking(callback: CallbackQuery, **kwargs):
    booking_id = callback.data.split(":")[1]
    booking = await db.get_booking(booking_id)
    if not booking:
        await callback.answer("Запись не найдена")
        return

    user = await db.get_user(booking["user_id"])
    svc = SERVICES.get(booking["service_key"], {"name": "?", "price": 0})

    status_map = {
        "pending": "⏳ Ожидает", "confirmed": "✅ Подтверждена",
        "cancelled": "❌ Отменена", "done": "🏁 Выполнена"
    }
    pay_map = {"unpaid": "💰 Не оплачено", "paid": "💚 Оплачено"}

    text = (
        f"📋 <b>Запись #{booking_id}</b>\n\n"
        f"👤 Клиент: {user['full_name'] if user else 'N/A'}\n"
        f"📱 Телефон: {user['phone'] if user else 'N/A'}\n"
        f"@{user['username'] if user and user['username'] else 'нет'}\n\n"
        f"🛎 Услуга: {svc['name']}\n"
        f"💰 Стоимость: {svc['price']}₽\n"
        f"📅 Дата: {booking['date']}\n"
        f"⏰ Время: {booking['time']}\n"
        f"📌 Статус: {status_map.get(booking['status'])}\n"
        f"💳 Оплата: {pay_map.get(booking['payment_status'])}"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=admin_booking_kb(booking_id),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback.answer()


@router.callback_query(F.data.startswith("admin_confirm:"))
@admin_only
async def admin_confirm_booking(callback: CallbackQuery, bot: Bot, **kwargs):
    booking_id = callback.data.split(":")[1]
    await db.update_booking_status(booking_id, "confirmed")
    booking = await db.get_booking(booking_id)
    svc = SERVICES.get(booking["service_key"], {"name": "?"})

    await callback.answer("✅ Запись подтверждена!")
    
    # Пытаемся обновить клавиатуру, игнорируем ошибку, если она не изменилась
    try:
        await callback.message.edit_reply_markup(reply_markup=admin_booking_kb(booking_id))
    except TelegramBadRequest:
        pass 

    # Notify user
    try:
        await bot.send_message(
            booking["user_id"],
            f"✅ <b>Ваша запись подтверждена!</b>\n\n"
            f"🛎 {svc['name']}\n"
            f"📅 {booking['date']} в {booking['time']}\n\n"
            f"Ждём вас!",
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("admin_cancel:"))
@admin_only
async def admin_cancel_booking(callback: CallbackQuery, bot: Bot, **kwargs):
    booking_id = callback.data.split(":")[1]
    await db.cancel_booking(booking_id)
    booking = await db.get_booking(booking_id)

    await callback.answer("❌ Запись отменена")
    
    try:
        await callback.message.edit_reply_markup(reply_markup=admin_booking_kb(booking_id))
    except TelegramBadRequest:
        pass

    try:
        await bot.send_message(
            booking["user_id"],
            f"❌ <b>Ваша запись была отменена администратором.</b>\n\n"
            f"Если у вас есть вопросы, свяжитесь с нами.",
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("admin_done:"))
@admin_only
async def admin_done_booking(callback: CallbackQuery, bot: Bot, **kwargs):
    booking_id = callback.data.split(":")[1]
    await db.update_booking_status(booking_id, "done")
    await callback.answer("🏁 Отмечено как выполненное!")

    booking = await db.get_booking(booking_id)
    try:
        await bot.send_message(
            booking["user_id"],
            f"🏁 Ваша запись завершена.\n\nСпасибо, что воспользовались нашими услугами! ❤️"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("admin_paid:"))
@admin_only
async def admin_mark_paid(callback: CallbackQuery, bot: Bot, **kwargs):
    booking_id = callback.data.split(":")[1]
    await db.update_payment_status(booking_id, "paid")
    await callback.answer("💚 Оплата отмечена!")

    booking = await db.get_booking(booking_id)
    try:
        await bot.send_message(
            booking["user_id"],
            f"💚 Оплата по вашей записи подтверждена!"
        )
    except Exception:
        pass


# ──────────────── USERS ────────────────

@router.callback_query(F.data == "admin:users")
@admin_only
async def admin_users(callback: CallbackQuery, **kwargs):
    users = await db.get_all_users()
    text = f"👥 <b>Клиенты ({len(users)})</b>\n\n"
    for u in users[:20]:
        text += f"• {u['full_name']} (@{u['username'] or 'нет'}) 📱{u['phone'] or '?'}\n"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=admin_menu_kb(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback.answer()


# ──────────────── РАССЫЛКА ────────────────

@router.callback_query(F.data == "admin:broadcast")
@admin_only
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.message.answer("📢 Введите текст для рассылки всем пользователям:")
    await state.set_state(AdminBroadcast.waiting_message)


@router.message(AdminBroadcast.waiting_message)
@admin_only
async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot, **kwargs):
    await state.clear()
    users = await db.get_all_users()
    sent = 0
    failed = 0
    for user in users:
        try:
            await bot.send_message(user["user_id"], f"📢 <b>Сообщение от администратора:</b>\n\n{message.text}", parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"📢 Рассылка завершена!\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}")


# ──────────────── QUICK COMMANDS ────────────────

@router.message(Command("bookings"))
@admin_only
async def cmd_bookings(message: Message, **kwargs):
    bookings = await db.get_all_bookings(status="pending")
    if not bookings:
        await message.answer("Нет ожидающих записей.")
        return
    text = f"⏳ <b>Ожидают подтверждения ({len(bookings)}):</b>\n\n"
    for b in bookings:
        svc = SERVICES.get(b["service_key"], {"name": "?"})
        b_id = str(b.get("_id", b.get("id")))
        text += f"#{b_id} | {b['full_name']} | {b['date']} {b['time']} | {svc['name']}\n"
    await message.answer(text, parse_mode="HTML")


@router.message(Command("stats"))
@admin_only
async def cmd_stats(message: Message, **kwargs):
    stats = await db.get_stats()
    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"📋 Всего записей: {stats['total_bookings']}\n"
        f"⏳ Ожидают: {stats['pending']}\n"
        f"✅ Подтверждено: {stats['confirmed']}\n"
        f"💚 Оплачено: {stats['paid']}",
        parse_mode="HTML"
    )