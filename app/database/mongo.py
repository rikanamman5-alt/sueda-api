import ssl
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import MONGO_URI, DB_NAME

parsed = urlparse(MONGO_URI)
qs = parse_qs(parsed.query)
qs['tls'] = ['true']
qs['tlsInsecure'] = ['true']
qs['tlsAllowInvalidCertificates'] = ['true']
qs['tlsAllowInvalidHostnames'] = ['true']
qs['retryWrites'] = ['true']
qs['w'] = ['majority']
new_query = urlencode(qs, doseq=True)
patched_uri = urlunparse(parsed._replace(query=new_query))

client = AsyncIOMotorClient(patched_uri)
db = client[DB_NAME]