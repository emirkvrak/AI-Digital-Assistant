import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY .env dosyasında belirtilmelidir!")

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "chatbot")

    MAIL_SERVER = os.getenv("MAIL_SERVER", "127.0.0.1")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 1025))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "false").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv(
        "MAIL_DEFAULT_SENDER",
        MAIL_USERNAME or "noreply@ai-digital-assistant.local"
    )
    MAIL_TIMEOUT = int(os.getenv("MAIL_TIMEOUT", 10))

    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
    VERIFY_EMAIL_TOKEN_EXPIRE_MINUTES = int(os.getenv("VERIFY_EMAIL_TOKEN_EXPIRE_MINUTES", 60))
    RESET_PASSWORD_TOKEN_EXPIRE_MINUTES = int(os.getenv("RESET_PASSWORD_TOKEN_EXPIRE_MINUTES", 60))

    IS_PRODUCTION = os.getenv("IS_PRODUCTION", "false").lower() == "true"
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
  
    MODEL_API_URL = os.getenv("MODEL_API_URL", "http://localhost:5005")
