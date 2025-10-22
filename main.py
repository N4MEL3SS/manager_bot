import asyncio
import logging
import signal
import sys

from database import db
from manager_bot import run_manager_bot
from n8n_webhook import run_n8n_webhook
from notifications import notification_manager

from config import config


# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def create_default_admin():
    """Создание администратора по умолчани."""
    if config.ADMIN_CHAT_IDS:
        for admin_chat_id in config.ADMIN_CHAT_IDS:
            try:
                existing_manager = await db.get_manager_by_chat_id(admin_chat_id)
                if not existing_manager:
                    await db.add_manager(admin_chat_id, "Администратор")
                    logging.info(f"Default admin created: {admin_chat_id}")
                elif not existing_manager.is_active:
                    existing_manager.is_active = True
                    logging.info(f"Admin reactivated: {admin_chat_id}")
            except Exception as e:
                logging.error(f"Error creating default admin {admin_chat_id}: {e}")


async def main():
    """Основная функция запуска."""
    logger.info("Starting Ticket Management System with N8N integration...")

    # Инициализация базы данных
    await db.init_db()

    # Создание администраторов по умолчанию
    await create_default_admin()

    # Запуск сервисов
    await asyncio.gather(run_manager_bot(), run_n8n_webhook(), return_exceptions=True)


def signal_handler(sig, frame):
    """Обработчик сигналов для graceful shutdown."""
    logger.info("Received shutdown signal...")
    asyncio.create_task(shutdown())


async def shutdown():
    """Корректное завершение работы."""
    logger.info("Shutting down services...")
    await notification_manager.close()
    sys.exit(0)


if __name__ == "__main__":
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Services stopped by user")
    except Exception as e:
        logger.error(f"Error running services: {e}")
