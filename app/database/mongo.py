import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import MONGO_URI, DB_NAME

client = AsyncIOMotorClient(
    MONGO_URI,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=30000,
)
db = client[DB_NAME]
