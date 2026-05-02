# 🤖 Telegram Bot — Запись клиентов + Оплата

Полнофункциональный бот для записи клиентов с админ-панелью и симуляцией оплаты.

---

## 🚀 Быстрый старт

### 1. Создай бота
- Открой [@BotFather](https://t.me/BotFather) в Telegram
- Отправь `/newbot`
- Скопируй **BOT_TOKEN**

### 2. Установи зависимости
```bash
pip install -r requirements.txt
```

### 3. Настрой конфиг
Открой `config.py` и измени:
```python
BOT_TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"
ADMIN_IDS = [ВАШ_TELEGRAM_ID]  # получи у @userinfobot
```

Или создай `.env` файл:
```
BOT_TOKEN=1234567890:ABCdef...
```

### 4. Запусти
```bash
python bot.py
```

---

## 📁 Структура проекта

```
tg_booking_bot/
├── bot.py           # Точка входа
├── config.py        # Настройки (токен, услуги, часы работы)
├── database.py      # SQLite база данных
├── keyboards.py     # Все клавиатуры
├── states.py        # FSM состояния
├── handlers/
│   ├── client.py    # Клиентская часть
│   ├── admin.py     # Админ-панель
│   └── payment.py   # Оплата
└── requirements.txt
```

---

## ⚙️ Настройка услуг (config.py)

```python
SERVICES = {
    "haircut": {"name": "✂️ Стрижка", "price": 1500, "duration": 60},
    "coloring": {"name": "🎨 Покраска", "price": 3500, "duration": 120},
    # добавь свои услуги...
}
```

## 🕐 Настройка рабочих часов

```python
WORK_HOURS = {
    "start": 9,        # начало в 9:00
    "end": 20,         # конец в 20:00
    "slot_minutes": 30 # слот каждые 30 минут
}
WORK_DAYS = [0, 1, 2, 3, 4, 5]  # 0=Пн, 6=Вс
```

---

## 👤 Функции клиента

| Кнопка | Функция |
|--------|---------|
| 📅 Записаться | Выбор услуги → дата → время → подтверждение |
| 📋 Мои записи | Просмотр всех записей с деталями |
| 💳 Оплатить | Оплата неоплаченных записей |
| 👤 Мой профиль | Данные пользователя и статистика |
| 📞 Контакты | Контактная информация |

---

## 🔐 Функции администратора

Команды:
- `/admin` — открыть панель администратора
- `/bookings` — ожидающие записи
- `/stats` — статистика

Через панель:
- 📋 Все записи / ⏳ Ожидают
- ✅ Подтвердить / ❌ Отменить запись
- 🏁 Отметить выполненной
- 💚 Отметить оплаченной
- 👥 Список клиентов
- 📢 Рассылка всем пользователям

---

## 💳 Оплата

### Симуляция (уже работает)
Нажми «💳 Симуляция оплаты» → система имитирует платёж и помечает запись оплаченной.

### Stripe + Telegram Payments
1. Получи ключ у [@BotFather](https://t.me/BotFather) → Payments
2. Добавь в `.env`: `STRIPE_SECRET_KEY=sk_test_...`
3. Раскомментируй блок в `handlers/payment.py`

---

## 🗄 База данных

SQLite файл `bookings.db` создаётся автоматически.

Таблицы:
- `users` — зарегистрированные пользователи
- `bookings` — все записи

Статусы записей: `pending` → `confirmed` → `done` / `cancelled`
Статусы оплаты: `unpaid` / `paid`

---

## 🌐 Деплой на сервер

```bash
# Systemd сервис
sudo nano /etc/systemd/system/booking-bot.service

[Unit]
Description=Booking Telegram Bot
After=network.target

[Service]
WorkingDirectory=/path/to/tg_booking_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
Environment=BOT_TOKEN=your_token

[Install]
WantedBy=multi-user.target

sudo systemctl enable booking-bot
sudo systemctl start booking-bot
```
