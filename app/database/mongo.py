import ssl
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import MONGO_URI, DB_NAME

tls_ctx = ssl.create_default_context()
tls_ctx.check_hostname = False
tls_ctx.verify_mode = ssl.CERT_NONE
try:
    tls_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    tls_ctx.maximum_version = ssl.TLSVersion.TLSv1_2
except AttributeError:
    pass
client = AsyncIOMotorClient(MONGO_URI, tls_context=tls_ctx, tls=True)
db = client[DB_NAME]
