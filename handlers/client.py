import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from config import SERVICES
from keyboards import (
    main_menu_kb, phone_request_kb, services_kb,
    dates_kb, times_kb, confirm_booking_kb, my_bookings_kb,
    admin_booking_kb, payment_kb, remove_kb
)
from states import Registration, Booking

logger = logging.getLogger(__name__)
router = Router()


# ──────────────── /START ────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)

    if not user:
        await db.register_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name
        )

    if user and user.get("phone"):
        await message.answer(
            f"👋 Добро пожаловать, <b>{message.from_user.first_name}</b>!\n\n"
            "Выберите действие в меню:",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
            "Для записи нам нужен ваш номер телефона.\n"
            "Нажмите кнопку ниже:",
            reply_markup=phone_request_kb(),
            parse_mode="HTML"
        )
        await state.set_state(Registration.waiting_phone)


@router.message(Registration.waiting_phone, F.contact)
async def get_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await db.update_phone(message.from_user.id, phone)
    await state.clear()
    await message.answer(
        "✅ Телефон сохранён!\n\nВыберите действие:",
        reply_markup=main_menu_kb()
    )


@router.message(Registration.waiting_phone, F.text == "⬅️ Назад")
async def back_from_phone(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu_kb())


# ──────────────── ГЛАВНОЕ МЕНЮ ────────────────

@router.message(F.text == "👤 Мой профиль")
async def my_profile(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        return
    bookings = await db.get_user_bookings(message.from_user.id)
    total = len(bookings)
    done = sum(1 for b in bookings if b["status"] == "done")
    text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"📛 Имя: {user['full_name']}\n"
        f"📱 Телефон: {user['phone'] or 'не указан'}\n"
        f"📅 Всего записей: {total}\n"
        f"✅ Выполнено: {done}\n"
        f"🗓 С нами с: {user['registered_at'][:10]}"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "📞 Контакты")
async def contacts(message: Message):
    await message.answer(
        "📞 <b>Контакты</b>\n\n"
        "📍 Адрес: ул. Примерная, 1\n"
        "📱 Телефон: +7 (999) 123-45-67\n"
        "🕐 Режим работы: Пн-Сб 9:00–20:00\n"
        "📬 Email: info@example.com",
        parse_mode="HTML"
    )


# ──────────────── ЗАПИСЬ ────────────────

@router.message(F.text == "📅 Записаться")
async def start_booking(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user or not user.get("phone"):
        await message.answer(
            "Сначала укажите номер телефона:",
            reply_markup=phone_request_kb()
        )
        await state.set_state(Registration.waiting_phone)
        return

    await state.clear()
    await message.answer(
        "🛎 <b>Выберите услугу:</b>",
        reply_markup=services_kb(),
        parse_mode="HTML"
    )
    await state.set_state(Booking.choosing_service)


@router.callback_query(Booking.choosing_service, F.data.startswith("service:"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":")[1]
    svc = SERVICES[key]
    await state.update_data(service_key=key)
    await callback.message.edit_text(
        f"✅ Услуга: <b>{svc['name']}</b>\n"
        f"💰 Цена: {svc['price']}₽ | ⏱ {svc['duration']} мин\n\n"
        f"📅 <b>Выберите дату:</b>",
        reply_markup=dates_kb(),
        parse_mode="HTML"
    )
    await state.set_state(Booking.choosing_date)


@router.callback_query(F.data == "back:services")
async def back_to_services(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🛎 <b>Выберите услугу:</b>",
        reply_markup=services_kb(),
        parse_mode="HTML"
    )
    await state.set_state(Booking.choosing_service)


@router.callback_query(Booking.choosing_date, F.data.startswith("date:"))
async def choose_date(callback: CallbackQuery, state: FSMContext):
    date = callback.data.split(":")[1]
    await state.update_data(date=date)

    # Get taken slots
    all_bookings = await db.get_all_bookings()
    taken = [b["time"] for b in all_bookings if b["date"] == date and b["status"] != "cancelled"]

    await callback.message.edit_text(
        f"📅 Дата: <b>{date}</b>\n\n⏰ <b>Выберите время:</b>",
        reply_markup=times_kb(date, taken),
        parse_mode="HTML"
    )
    await state.set_state(Booking.choosing_time)


@router.callback_query(F.data == "back:dates")
async def back_to_dates(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📅 <b>Выберите дату:</b>",
        reply_markup=dates_kb(),
        parse_mode="HTML"
    )
    await state.set_state(Booking.choosing_date)


@router.callback_query(F.data == "slot_taken")
async def slot_taken(callback: CallbackQuery):
    await callback.answer("❌ Это время уже занято!", show_alert=True)


@router.callback_query(Booking.choosing_time, F.data.startswith("time:"))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    time = callback.data.split(":")[1]
    data = await state.get_data()
    await state.update_data(time=time)

    service_key = data["service_key"]
    date = data["date"]
    svc = SERVICES[service_key]

    # Create booking
    booking_id = await db.create_booking(
        callback.from_user.id, service_key, date, time
    )

    await callback.message.edit_text(
        f"📝 <b>Ваша запись:</b>\n\n"
        f"🛎 Услуга: {svc['name']}\n"
        f"💰 Стоимость: {svc['price']}₽\n"
        f"📅 Дата: {date}\n"
        f"⏰ Время: {time}\n"
        f"⏱ Длительность: {svc['duration']} мин\n\n"
        f"Статус: ⏳ Ожидает подтверждения\n\n"
        f"Нажмите <b>«Оплатить сейчас»</b> чтобы оплатить заранее:",
        reply_markup=confirm_booking_kb(booking_id),
        parse_mode="HTML"
    )
    await state.clear()

    # Notify admins
    from config import ADMIN_IDS
    from aiogram import Bot
    bot = callback.bot
    user = await db.get_user(callback.from_user.id)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🔔 <b>Новая запись #{booking_id}</b>\n"
                f"👤 {user['full_name']} (@{user['username']})\n"
                f"📱 {user['phone']}\n"
                f"🛎 {svc['name']}\n"
                f"📅 {date} в {time}",
                reply_markup=admin_booking_kb(booking_id),
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("cancel_booking:"))
async def cancel_booking_cb(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])
    await db.cancel_booking(booking_id)
    await callback.message.edit_text(
        "❌ <b>Запись отменена.</b>\n\nЧтобы записаться снова, нажмите «📅 Записаться»",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("confirm_booking:"))
async def confirm_booking_cb(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])
    booking = await db.get_booking(booking_id)
    if not booking:
        await callback.answer("Запись не найдена")
        return
    svc = SERVICES[booking["service_key"]]
    await callback.message.edit_text(
        f"✅ <b>Запись #{booking_id} подтверждена!</b>\n\n"
        f"🛎 {svc['name']}\n"
        f"📅 {booking['date']} в {booking['time']}\n"
        f"💰 {svc['price']}₽\n\n"
        f"Ждём вас! Оплатить можно через кнопку «💳 Оплатить» в главном меню.",
        parse_mode="HTML"
    )


# ──────────────── МОИ ЗАПИСИ ────────────────

@router.message(F.text == "📋 Мои записи")
async def my_bookings(message: Message):
    bookings = await db.get_user_bookings(message.from_user.id)
    if not bookings:
        await message.answer("У вас пока нет записей.\n\nНажмите «📅 Записаться» чтобы создать запись.")
        return

    active = [b for b in bookings if b["status"] not in ("cancelled", "done")]
    past = [b for b in bookings if b["status"] in ("cancelled", "done")]

    text = f"📋 <b>Ваши записи</b> (всего: {len(bookings)})\n\n"
    text += f"✅ Активных: {len(active)} | 🏁 Завершённых: {len(past)}"

    await message.answer(
        text,
        reply_markup=my_bookings_kb(bookings[:10]),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("view_booking:"))
async def view_booking(callback: CallbackQuery):
    booking_id = callback.data.split(":")[1] # Оставляем строкой для универсальности
    booking = await db.get_booking(booking_id)
    
    if not booking:
        await callback.answer("Запись не найдена")
        return

    svc = SERVICES.get(booking["service_key"], {"name": "Неизвестно", "price": 0})
    status_map = {
        "pending": "⏳ Ожидает подтверждения",
        "confirmed": "✅ Подтверждена",
        "cancelled": "❌ Отменена",
        "done": "🏁 Выполнена"
    }
    pay_map = {"unpaid": "💰 Не оплачено", "paid": "💚 Оплачено"}

    text = (
        f"📋 <b>Запись #{booking_id}</b>\n\n"
        f"🛎 Услуга: {svc['name']}\n"
        f"💰 Стоимость: {svc['price']}₽\n"
        f"📅 Дата: {booking['date']}\n"
        f"⏰ Время: {booking['time']}\n"
        f"📌 Статус: {status_map.get(booking['status'], booking['status'])}\n"
        f"💳 Оплата: {pay_map.get(booking['payment_status'], booking['payment_status'])}"
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    if booking["status"] not in ("cancelled", "done"):
        builder.button(text="💳 Оплатить", callback_data=f"pay:{booking_id}")
        builder.button(text="❌ Отменить", callback_data=f"cancel_booking:{booking_id}")
    builder.button(text="⬅️ Назад", callback_data="back_to_bookings")
    builder.adjust(2)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "back_to_bookings")
async def back_to_bookings(callback: CallbackQuery):
    bookings = await db.get_user_bookings(callback.from_user.id)
    await callback.message.edit_text(
        f"📋 <b>Ваши записи</b>",
        reply_markup=my_bookings_kb(bookings[:10]),
        parse_mode="HTML"
    )


# ──────────────── ОПЛАТА (через меню) ────────────────

@router.message(F.text == "💳 Оплатить")
async def payment_menu(message: Message):
    bookings = await db.get_user_bookings(message.from_user.id)
    unpaid = [b for b in bookings if b["payment_status"] == "unpaid" and b["status"] != "cancelled"]
    if not unpaid:
        await message.answer("✅ У вас нет неоплаченных записей!")
        return
    await message.answer(
        f"💳 <b>Неоплаченные записи ({len(unpaid)})</b>\n\nВыберите запись для оплаты:",
        reply_markup=my_bookings_kb(unpaid),
        parse_mode="HTML"
    )
