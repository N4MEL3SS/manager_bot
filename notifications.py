import asyncio
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from config import config
from datetime import datetime, timedelta
import pytz


logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self):
        self.bot = None
        self.last_notification_time = {}
        self.cooldown = timedelta(seconds=config.NOTIFICATION_COOLDOWN)
    
    async def initialize(self):
        """Инициализация бота для уведомлений"""
        self.bot = Bot(token=config.MANAGER_BOT_TOKEN)
    
    async def close(self):
        """Закрытие бота"""
        if self.bot:
            await self.bot.session.close()
    
    def can_send_notification(self, manager_chat_id: int) -> bool:
        """Проверка, можно ли отправлять уведомление (анти-спам)"""
        now = datetime.now(pytz.timezone(config.TIMEZONE))
        last_time = self.last_notification_time.get(manager_chat_id)
        
        if not last_time:
            return True
        
        return (now - last_time) >= self.cooldown
    
    def update_notification_time(self, manager_chat_id: int):
        """Обновление времени последнего уведомления"""
        self.last_notification_time[manager_chat_id] = datetime.now(pytz.timezone(config.TIMEZONE))
    
    async def notify_new_ticket(self, ticket):
        """Уведомление менеджеров о новом тикете"""
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
                            disable_notification=False  # Важное уведомление - показываем звук
                        )
                        self.update_notification_time(manager.chat_id)
                        successful_notifications += 1
                        logger.info(f"New ticket notification sent to manager {manager.nickname}")
                        
                        # Небольшая задержка между отправками, чтобы не спамить
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"Failed to send notification to manager {manager.chat_id}: {e}")
                        # Если менеджер заблокировал бота, можно деактивировать его
                        # await db.remove_manager(manager.chat_id)
            
            logger.info(f"New ticket notifications sent: {successful_notifications}/{len(managers)}")
            
        except Exception as e:
            logger.error(f"Error in notify_new_ticket: {e}")
    
    async def notify_ticket_answered(self, ticket, answering_manager_chat_id):
        """Уведомление других менеджеров о том, что тикет взят в работу"""
        if not self.bot:
            await self.initialize()
        
        try:
            managers = await db.get_managers_for_notifications()
            
            # Фильтруем менеджера, который ответил на тикет
            other_managers = [m for m in managers if m.chat_id != answering_manager_chat_id]
            
            if not other_managers:
                return
            
            answering_manager = await db.get_manager_by_chat_id(answering_manager_chat_id)
            manager_name = answering_manager.nickname if answering_manager else "Неизвестный менеджер"
            
            notification_text = f"""
📋 Тикет взят в работу

🆔 Тикет: #{ticket.id}
👤 Клиент: @{ticket.client_nickname}
👨‍💼 Менеджер: {manager_name}
⏰ Время: {datetime.now(pytz.timezone(config.TIMEZONE)).strftime('%H:%M %d.%m.%Y')}

Тикет больше не требует внимания.
            """
            
            for manager in other_managers:
                try:
                    await self.bot.send_message(
                        chat_id=manager.chat_id,
                        text=notification_text,
                        disable_notification=True  # Тихие уведомления для этой информации
                    )
                except Exception as e:
                    logger.error(f"Failed to send ticket answered notification to manager {manager.chat_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error in notify_ticket_answered: {e}")
    
    async def notify_daily_stats(self):
        """Ежедневная статистика для менеджеров"""
        if not self.bot:
            await self.initialize()
        
        try:
            managers = await db.get_managers_for_notifications()
            tickets_stats = await db.get_tickets_count()
            
            stats_text = self._format_daily_stats(tickets_stats)
            
            for manager in managers:
                try:
                    # Получаем персональную статистику менеджера
                    personal_stats = await db.get_manager_stats(manager.chat_id)
                    
                    personal_text = f"\n👤 Ваша статистика:\n"
                    personal_text += f"   • Отвечено тикетов: {personal_stats['total_answered']}\n"
                    if personal_stats['last_activity']:
                        personal_text += f"   • Последняя активность: {personal_stats['last_activity'].strftime('%H:%M %d.%m.%Y')}\n"
                    else:
                        personal_text += f"   • Последняя активность: нет данных\n"
                    
                    full_text = stats_text + personal_text
                    
                    await self.bot.send_message(
                        chat_id=manager.chat_id,
                        text=full_text,
                        disable_notification=True
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to send daily stats to manager {manager.chat_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error in notify_daily_stats: {e}")
    
    async def _format_new_ticket_notification(self, ticket, tickets_stats: dict) -> str:
        """Форматирование текста уведомления о новом тикете"""
        return f"""
🚨 НОВЫЙ ТИКЕТ

🆔 Номер: #{ticket.id}
👤 Пользователь: @{ticket.client_nickname}
⏰ Время: {ticket.created_at.strftime('%H:%M %d.%m.%Y')}
❓ Вопрос:
{ticket.question[:300]}{'...' if len(ticket.question) > 300 else ''}

📊 Неотвеченных тикетов: {tickets_stats['pending']}
        """
    
    def _create_ticket_notification_keyboard(self, ticket_id: int):
        """Создание клавиатуры для уведомления о тикете"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📝 Ответить на тикет", callback_data=f"answer_{ticket_id}")],
                [InlineKeyboardButton(text="🎫 Все тикеты", callback_data="show_tickets")]
            ]
        )
    
    def _format_daily_stats(self, tickets_stats: dict) -> str:
        """Форматирование ежедневной статистики"""
        return f"""
📊 ЕЖЕДНЕВНАЯ СТАТИСТИКА

📈 Общая статистика:
   • Всего тикетов: {tickets_stats['total']}
   • Неотвеченных: {tickets_stats['pending']}
   • Отвеченных: {tickets_stats['answered']}

⏰ Время: {datetime.now(pytz.timezone(config.TIMEZONE)).strftime('%H:%M %d.%m.%Y')}
        """

# Глобальный экземпляр менеджера уведомлений
notification_manager = NotificationManager()