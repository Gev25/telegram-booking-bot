import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, LabeledPrice, PreCheckoutQuery, Message

import database as db
from config import SERVICES
from keyboards import payment_kb

# Настройка логирования
logger = logging.getLogger(__name__)
router = Router()

# ──────────────── ВЫБОР ОПЛАТЫ ────────────────

@router.callback_query(F.data.startswith("pay:"))
async def pay_booking(callback: CallbackQuery):
    # Получаем ID как строку (для MongoDB)
    booking_id = callback.data.split(":")[1]
    booking = await db.get_booking(booking_id)
    
    if not booking:
        await callback.answer("❌ Запись не найдена", show_alert=True)
        return

    if booking.get("payment_status") == "paid":
        await callback.answer("✅ Эта запись уже оплачена!", show_alert=True)
        return

    svc = SERVICES.get(booking["service_key"], {"name": "Услуга", "price": 0})

    text = (
        f"💳 <b>Оплата записи #{booking_id}</b>\n\n"
        f"🛎 Услуга: <b>{svc['name']}</b>\n"
        f"📅 Дата: <b>{booking['date']}</b>\n"
        f"⏰ Время: <b>{booking['time']}</b>\n\n"
        f"Стоимость: <b>{svc['price']} ⭐ (Telegram Stars)</b>\n\n"
        f"Нажмите кнопку ниже для перехода к оплате 👇"
    )

    await callback.message.edit_text(
        text, 
        reply_markup=payment_kb(booking_id), 
        parse_mode="HTML"
    )


# ──────────────── СОЗДАНИЕ ИНВОЙСА STARS ────────────────

@router.callback_query(F.data.startswith("stars_pay:"))
async def send_stars_invoice(callback: CallbackQuery, bot: Bot):
    booking_id = callback.data.split(":")[1]
    booking = await db.get_booking(booking_id)
    
    if not booking:
        await callback.answer("Ошибка: запись не найдена")
        return

    svc = SERVICES.get(booking["service_key"], {"name": "Услуга", "price": 1})

    # Список цен (для Stars количество указывается напрямую в amount)
    prices = [LabeledPrice(label=svc["name"], amount=svc["price"])]

    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Оплата: {svc['name']}",
            description=f"Запись на {booking['date']} в {booking['time']}",
            prices=prices,
            payload=f"booking_id:{booking_id}",  # Важно для обработки после оплаты
            provider_token="",                   # Для Stars всегда пусто
            currency="XTR",                      # Валюта Telegram Stars
            start_parameter="booking-stars-payment"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка создания счета Stars: {e}")
        await callback.answer("❌ Ошибка при формировании счета", show_alert=True)


# ──────────────── ПРОВЕРКА ПЕРЕД ПЛАТЕЖОМ (ОБЯЗАТЕЛЬНО) ────────────────

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    # Здесь можно добавить проверку, не занято ли еще время, но обычно просто True
    await pre_checkout_query.answer(ok=True)


# ──────────────── УСПЕШНЫЙ ПЛАТЕЖ ────────────────

@router.message(F.successful_payment)
async def on_successful_payment(message: Message, bot: Bot):
    # Достаем ID из payload
    payload = message.successful_payment.invoice_payload
    booking_id = payload.split(":")[1]

    # Обновляем статус в БД
    await db.update_payment_status(booking_id, "paid")
    
    await message.answer(
        f"🌟 <b>Оплата прошла успешно!</b>\n\n"
        f"Запись №{booking_id} теперь имеет статус «Оплачено».\n"
        f"Спасибо за использование нашего сервиса!",
        parse_mode="HTML"
    )

    # Уведомление администратора
    from config import ADMIN_IDS
    if ADMIN_IDS:
        booking = await db.get_booking(booking_id)
        admin_text = (
            f"💰 <b>НОВАЯ ОПЛАТА STARS</b>\n\n"
            f"Запись: <code>{booking_id}</code>\n"
            f"Клиент: {booking.get('full_name', 'Не указано')}\n"
            f"Сумма: {message.successful_payment.total_amount} ⭐"
        )
        try:
            await bot.send_message(ADMIN_IDS[0], admin_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка уведомления админа: {e}")