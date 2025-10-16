import asyncio
import logging
from database import db
from client_bot import run_client_bot
from manager_bot import run_manager_bot
from notifications import notification_manager
from config import config
import signal
import sys


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_default_admin():
    """Создание администратора по умолчанию (если указан в конфиге)"""
    if config.ADMIN_CHAT_IDS:
        for admin_chat_id in config.ADMIN_CHAT_IDS:
            try:
                # Проверяем, существует ли уже админ
                existing_manager = await db.get_manager_by_chat_id(admin_chat_id)
                if not existing_manager:
                    await db.add_manager(admin_chat_id, "Администратор")
                    logging.info(f"Default admin created: {admin_chat_id}")
                elif not existing_manager.is_active:
                    existing_manager.is_active = True
                    logging.info(f"Admin reactivated: {admin_chat_id}")
            except Exception as e:
                logging.error(f"Error creating default admin {admin_chat_id}: {e}")

async def scheduled_tasks():
    """Запланированные задачи (ежедневная статистика и т.д.)"""
    import asyncio
    from datetime import datetime
    import pytz
    
    while True:
        try:
            now = datetime.now(pytz.timezone(config.TIMEZONE))
            
            # Ежедневная статистика в 09:00
            if now.hour == 9 and now.minute == 0:
                await notification_manager.notify_daily_stats()
                logging.info("Daily stats notification sent")
                # Ждем 61 минуту чтобы не отправлять повторно
                await asyncio.sleep(61 * 60)
            else:
                # Проверяем каждую минуту
                await asyncio.sleep(60)
                
        except Exception as e:
            logging.error(f"Error in scheduled tasks: {e}")
            await asyncio.sleep(60)

async def main():
    """Основная функция запуска ботов"""
    logger.info("Starting Telegram bots with notifications...")
    
    # Инициализация базы данных
    await db.init_db()
    
    # Создание администраторов по умолчанию
    await create_default_admin()
    
    # Запуск ботов и запланированных задач
    await asyncio.gather(
        run_client_bot(),
        run_manager_bot(),
        scheduled_tasks(),
        return_exceptions=True
    )

def signal_handler(sig, frame):
    """Обработчик сигналов для graceful shutdown"""
    logger.info("Received shutdown signal...")
    asyncio.create_task(shutdown())

async def shutdown():
    """Корректное завершение работы"""
    logger.info("Shutting down bots...")
    await notification_manager.close()
    sys.exit(0)

if __name__ == "__main__":
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bots stopped by user")
    except Exception as e:
        logger.error(f"Error running bots: {e}")