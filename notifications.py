import asyncio
from datetime import datetime, timedelta
import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import pytz

from database import db

from config import config


logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self):
        self.bot = None
        self.last_notification_time = {}
        self.cooldown = timedelta(seconds=config.NOTIFICATION_COOLDOWN)

    async def initialize(self):
        """Инициализация бота для уведомлений."""
        self.bot = Bot(token=config.MANAGER_BOT_TOKEN)

    async def close(self):
        """Закрытие бота."""
        if self.bot:
            await self.bot.session.close()

    def can_send_notification(self, manager_chat_id: int) -> bool:
        """Проверка, можно ли отправлять уведомление (анти-спам)."""
        now = datetime.now(pytz.timezone(config.TIMEZONE))
        last_time = self.last_notification_time.get(manager_chat_id)

        if not last_time:
            return True

        return (now - last_time) >= self.cooldown

    def update_notification_time(self, manager_chat_id: int):
        """Обновление времени последнего уведомления."""
        self.last_notification_time[manager_chat_id] = datetime.now(pytz.timezone(config.TIMEZONE))

    async def notify_new_ticket(self, ticket):
        """Уведомление менеджеров о новом тикете."""
        if not config.NOTIFY_MANAGERS_NEW_TICKETS:
            return

        if not self.bot:
            await self.initialize()

        try:
            managers = await db.get_managers_for_notifications()

            if not managers:
                logger.warning("No active managers found for notifications")
                return

            # Получаем статистику для уведомления
            tickets_stats = await db.get_tickets_count()
            notification_text = await self._format_new_ticket_notification(ticket, tickets_stats)
            keyboard = self._create_ticket_notification_keyboard(ticket.id)

            successful_notifications = 0

            for manager in managers:
                if self.can_send_notification(manager.chat_id):
                    try:
                        await self.bot.send_message(
                            chat_id=manager.chat_id,
                            text=notification_text,
                            reply_markup=keyboard,
                            disable_notification=False,
                        )
                        self.update_notification_time(manager.chat_id)
                        successful_notifications += 1
                        logger.info(f"New ticket notification sent to manager {manager.nickname}")

                        await asyncio.sleep(0.1)

                    except Exception as e:
                        logger.error(f"Failed to send notification to manager {manager.chat_id}: {e}")

            logger.info(f"New ticket notifications sent: {successful_notifications}/{len(managers)}")

        except Exception as e:
            logger.error(f"Error in notify_new_ticket: {e}")

    async def _format_new_ticket_notification(self, ticket, tickets_stats: dict) -> str:
        """Форматирование текста уведомления о новом тикете."""
        return f"""
🚨 НОВЫЙ ТИКЕТ ОТ КЛИЕНТА

🆔 Номер: #{ticket.id}
👤 Клиент: {ticket.client_nickname}
💬 Вопрос:
{ticket.question[:400]}{"..." if len(ticket.question) > 400 else ""}

⏰ Время: {ticket.created_at.strftime("%H:%M %d.%m.%Y")}
📊 Ожидают ответа: {tickets_stats["pending"]} тикетов
        """

    def _create_ticket_notification_keyboard(self, ticket_id: int):
        """Создание клавиатуры для уведомления о тикете."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📝 Ответить на тикет", callback_data=f"answer_{ticket_id}")],
                [InlineKeyboardButton(text="🎫 Все тикеты", callback_data="show_tickets")],
            ]
        )


# Глобальный экземпляр менеджера уведомлений
notification_manager = NotificationManager()
