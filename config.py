import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    # Токены ботов
    MANAGER_BOT_TOKEN = os.getenv("MANAGER_BOT_TOKEN")

    # Настройки базы данных
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///tickets.db")

    # Админ панель
    ADMIN_CHAT_IDS = list(map(int, os.getenv("ADMIN_CHAT_IDS", "").split(","))) if os.getenv("ADMIN_CHAT_IDS") else []

    # Настройки уведомлений
    NOTIFY_MANAGERS_NEW_TICKETS = os.getenv("NOTIFY_MANAGERS_NEW_TICKETS", "True").lower() == "true"
    NOTIFICATION_COOLDOWN = int(os.getenv("NOTIFICATION_COOLDOWN", "30"))

    # N8N Webhook настройки
    N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://n8n.aiflownow.ru/webhook-test")
    N8N_API_KEY = os.getenv("N8N_API_KEY", "")

    # Другие настройки
    MAX_TICKET_LENGTH = 1000
    TIMEZONE = "Europe/Moscow"


config = Config()
