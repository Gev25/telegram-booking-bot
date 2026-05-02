import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла, если он есть
load_dotenv()

# ===== НАСТРОЙКИ БОТА =====
# Рекомендуется хранить токен в переменных окружения (.env)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8637197044:AAGHBNMv06syU4REtS_ADtP8SmJEUGYcRGU")

# ===== ADMIN IDs =====
# Список ID пользователей, имеющих доступ к админ-панели
ADMIN_IDS = [
    '1381500667', # получи у @userinfobot
]

# ===== УСЛУГИ И ЦЕНЫ (В Telegram Stars) =====
# ВНИМАНИЕ: Цена ('price') теперь указывается в количестве Звезд (⭐)
SERVICES = {
    "haircut": {"name": "✂️ Стрижка", "price": 15, "duration": 60},
    "coloring": {"name": "🎨 Покраска", "price": 35, "duration": 120},
    "manicure": {"name": "💅 Маникюр", "price": 12, "duration": 90},
    "massage": {"name": "💆 Массаж", "price": 25, "duration": 60},
    "consultation": {"name": "📋 Консультация", "price": 5, "duration": 30},
}

# ===== РАБОЧЕЕ ВРЕМЯ =====
WORK_HOURS = {
    "start": 9,   # Начало работы (9:00)
    "end": 20,    # Конец работы (20:00)
    "slot_minutes": 30  # Длительность одного слота
}

# Рабочие дни недели
WORK_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

# ===== НАСТРОЙКИ MONGODB =====
# Если база данных на том же сервере, используйте 'mongodb://localhost:27017/'
# Если используете MongoDB Atlas, вставьте свою строку подключения сюда
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:xJiIkhNfELCsIboRDfeLvSXQVPVuMVoK@yamanote.proxy.rlwy.net:41578")
DB_NAME = "booking_bot_db"

# Путь к SQLite (оставляем для совместимости, если где-то в коде забыли удалить импорт)
DATABASE_PATH = "booking.db"