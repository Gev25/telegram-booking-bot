from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from datetime import datetime, timedelta
from config import SERVICES, WORK_HOURS, WORK_DAYS


# ──────────────── REPLY KEYBOARDS ────────────────

def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📅 Записаться"),
        KeyboardButton(text="📋 Мои записи"),
    )
    builder.row(
        KeyboardButton(text="💳 Оплатить"),
        KeyboardButton(text="📞 Контакты"),
    )
    builder.row(KeyboardButton(text="👤 Мой профиль"))
    return builder.as_markup(resize_keyboard=True)


def phone_request_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📱 Отправить номер телефона", request_contact=True))
    builder.add(KeyboardButton(text="⬅️ Назад"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def remove_kb():
    return ReplyKeyboardRemove()


# ──────────────── INLINE KEYBOARDS ────────────────

def services_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, svc in SERVICES.items():
        builder.button(
            text=f"{svc['name']} — {svc['price']} ⭐",
            callback_data=f"svc:{key}"
        )
    builder.adjust(1)
    return builder.as_markup()


def dates_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    now = datetime.now()
    for i in range(14):
        date_obj = now + timedelta(days=i)
        if date_obj.strftime("%A").lower() in WORK_DAYS:
            d_str = date_obj.strftime("%Y-%m-%d")
            builder.button(text=d_str, callback_data=f"date:{d_str}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_services"))
    return builder.as_markup()


def times_kb(available_times: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in available_times:
        builder.button(text=t, callback_data=f"time:{t}")
    builder.adjust(4)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_dates"))
    return builder.as_markup()


def confirm_booking_kb(booking_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Кнопка оплаты сразу после записи
    builder.button(text="💳 Оплатить сейчас", callback_data=f"pay:{booking_id}")
    builder.button(text="🏠 В главное меню", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()


def my_bookings_kb(bookings: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for b in bookings:
        status_emoji = {
            "pending": "⏳", "confirmed": "✅", "cancelled": "❌", "done": "🏁"
        }.get(b["status"], "❓")
        pay_emoji = "💚" if b.get("payment_status") == "paid" else "💰"
        
        # Безопасное получение ID (поддержка и SQLite, и MongoDB)
        b_id = b.get('id') or b.get('_id')
        
        builder.button(
            text=f"{status_emoji} {b['date']} {b['time']} {pay_emoji}",
            callback_data=f"view_booking:{b_id}"
        )
    builder.adjust(1)
    return builder.as_markup()


def payment_kb(booking_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # ОСНОВНАЯ КНОПКА ДЛЯ STARS
    builder.button(
        text="🌟 Оплатить (Telegram Stars)", 
        callback_data=f"stars_pay:{booking_id}"
    )
    builder.button(text="⬅️ Назад", callback_data=f"view_booking:{booking_id}")
    builder.adjust(1)
    return builder.as_markup()


# ──────────────── ADMIN KEYBOARDS ────────────────

def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Все записи", callback_data="admin:all_bookings")
    builder.button(text="⏳ Ожидают", callback_data="admin:pending_bookings")
    builder.button(text="👥 Клиенты", callback_data="admin:users")
    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.button(text="📢 Рассылка", callback_data="admin:broadcast")
    builder.adjust(2)
    return builder.as_markup()


def admin_booking_kb(booking_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"admin_confirm:{booking_id}")
    builder.button(text="❌ Отменить", callback_data=f"admin_cancel:{booking_id}")
    builder.button(text="🏁 Выполнено", callback_data=f"admin_done:{booking_id}")
    builder.button(text="💰 Оплачено (вручную)", callback_data=f"admin_paid:{booking_id}")
    builder.button(text="⬅️ Назад", callback_data="admin:all_bookings")
    builder.adjust(2)
    return builder.as_markup()