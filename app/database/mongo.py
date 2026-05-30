import ssl
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import MONGO_URI, DB_NAME

_original_create_default_context = ssl.create_default_context
def _patched_create_default_context(*args, **kwargs):
    ctx = _original_create_default_context(*args, **kwargs)
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
    except (AttributeError, ssl.SSLError):
        pass
    return ctx
ssl.create_default_context = _patched_create_default_context

client = AsyncIOMotorClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True, tlsAllowInvalidHostnames=True)
db = client[DB_NAME]