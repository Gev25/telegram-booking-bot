import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Настройки подключения
MONGO_URL = "mongodb://mongo:xJiIkhNfELCsIboRDfeLvSXQVPVuMVoK@yamanote.proxy.rlwy.net:41578"
DB_NAME = "booking_system"  # Название твоей базы данных

logger = logging.getLogger(__name__)

# Инициализация клиента
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Коллекции
users_col = db["users"]
bookings_col = db["bookings"]

async def init_db():
    """
    Инициализация индексов. 
    Индексы ускоряют поиск в базе, когда записей станет много.
    """
    try:
        # Уникальный индекс для user_id, чтобы избежать дублей
        await users_col.create_index("user_id", unique=True)
        # Индекс для поиска свободных слотов по дате
        await bookings_col.create_index([("date", 1), ("time", 1)])
        logger.info("MongoDB успешно инициализирована с индексами.")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы: {e}")


# ──────────────── USERS ────────────────

async def get_user(user_id: int) -> dict | None:
    user = await users_col.find_one({"user_id": user_id})
    return user


async def register_user(user_id: int, username: str, full_name: str) -> dict:
    user_data = {
        "user_id": user_id,
        "username": username or "",
        "full_name": full_name,
        "phone": None,
        "registered_at": datetime.now().isoformat(),
        "is_blocked": False
    }
    # upsert=True обновит данные, если пользователь есть, или создаст нового
    await users_col.update_one(
        {"user_id": user_id},
        {"$setOnInsert": user_data},
        upsert=True
    )
    return await get_user(user_id)


async def update_phone(user_id: int, phone: str):
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"phone": phone}}
    )


async def get_all_users() -> list[dict]:
    cursor = users_col.find().sort("registered_at", -1)
    return await cursor.to_list(length=None)


async def block_user(user_id: int, blocked: bool):
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"is_blocked": blocked}}
    )


# ──────────────── BOOKINGS ────────────────

async def create_booking(user_id: int, service_key: str, date: str, time: str) -> str:
    booking_data = {
        "user_id": user_id,
        "service_key": service_key,
        "date": date,
        "time": time,
        "status": "pending",
        "payment_status": "unpaid",
        "created_at": datetime.now().isoformat()
    }
    result = await bookings_col.insert_one(booking_data)
    # Возвращаем строковый ID созданного документа
    return str(result.inserted_id)


async def get_booking(booking_id: str) -> dict | None:
    # В MongoDB поиск по ID требует трансформации строки в ObjectId
    booking = await bookings_col.find_one({"_id": ObjectId(booking_id)})
    return booking


async def get_user_bookings(user_id: int) -> list[dict]:
    cursor = bookings_col.find({"user_id": user_id}).sort([("date", -1), ("time", -1)])
    return await cursor.to_list(length=None)


async def get_all_bookings(status: str = None) -> list[dict]:
    query = {"status": status} if status else {}
    
    # Чтобы сделать JOIN как в SQL, в MongoDB используется аггрегация (lookup)
    pipeline = [
        {"$match": query},
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "user_id",
                "as": "user_info"
            }
        },
        {"$unwind": "$user_info"},
        {
            "$project": {
                "user_id": 1, "service_key": 1, "date": 1, "time": 1,
                "status": 1, "payment_status": 1,
                "full_name": "$user_info.full_name",
                "username": "$user_info.username",
                "phone": "$user_info.phone"
            }
        },
        {"$sort": {"date": 1, "time": 1}}
    ]
    
    cursor = bookings_col.aggregate(pipeline)
    return await cursor.to_list(length=None)


async def update_booking_status(booking_id: str, status: str):
    await bookings_col.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": status}}
    )


async def update_payment_status(booking_id: str, status: str):
    await bookings_col.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"payment_status": status}}
    )


async def is_slot_taken(date: str, time: str) -> bool:
    count = await bookings_col.count_documents({
        "date": date,
        "time": time,
        "status": {"$ne": "cancelled"}
    })
    return count > 0


async def cancel_booking(booking_id: str):
    await update_booking_status(booking_id, "cancelled")


async def get_stats() -> dict:
    return {
        "total_users": await users_col.count_documents({}),
        "total_bookings": await bookings_col.count_documents({}),
        "pending": await bookings_col.count_documents({"status": "pending"}),
        "confirmed": await bookings_col.count_documents({"status": "confirmed"}),
        "paid": await bookings_col.count_documents({"payment_status": "paid"}),
    }