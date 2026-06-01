from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

# --- GOOGLE OAUTH CONFIGURATION ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google")
GOOGLE_IOS_REDIRECT_URI = os.getenv("GOOGLE_IOS_REDIRECT_URI", "com.googleusercontent.apps.463767430072-k5ivijiknp3pi8m9tq2rguo0ra9a4otj:/oauthredirect")
PAYMAYA_SECRET = os.getenv("PAYMAYA_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_EXPIRE_MINUTES = int(os.getenv("ACCESS_EXPIRE_MINUTES", "1440"))
REFRESH_EXPIRE_DAYS = int(os.getenv("REFRESH_EXPIRE_DAYS", "30"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# --- EMAIL / SMTP SETTINGS ---
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "sueda.app.test@gmail.com"
SMTP_PASS = "your-app-password-here"
SMTP_FROM = "sueda.app.test@gmail.com"
