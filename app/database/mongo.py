import ssl
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import MONGO_URI, DB_NAME

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
try:
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
except AttributeError:
    pass

client = AsyncIOMotorClient(
    MONGO_URI,
    tls=True,
    tls_context=ctx,
    serverSelectionTimeoutMS=30000,
)
db = client[DB_NAME]