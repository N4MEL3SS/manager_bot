from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from models import Base, Ticket, Manager
from config import config
import logging
from datetime import datetime
import pytz


logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.engine = create_async_engine(config.DATABASE_URL, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def init_db(self):
        """Инициализация базы данных"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized")
    
    async def create_ticket(self, client_chat_id: int, client_nickname: str, question: str) -> Ticket:
        """Создание нового тикета"""
        async with self.async_session() as session:
            ticket = Ticket(
                client_chat_id=client_chat_id,
                client_nickname=client_nickname,
                question=question
            )
            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)
            logger.info(f"New ticket created: {ticket.id}")
            return ticket
    
    async def get_pending_tickets(self) -> list[Ticket]:
        """Получение всех неотвеченных тикетов"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Ticket).where(Ticket.is_answered == False).order_by(Ticket.created_at)
            )
            return result.scalars().all()
    
    async def get_ticket_by_id(self, ticket_id: int) -> Ticket:
        """Получение тикета по ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Ticket).where(Ticket.id == ticket_id)
            )
            return result.scalar_one_or_none()
    
    async def answer_ticket(self, ticket_id: int, answer: str, manager_chat_id: int) -> Ticket:
        """Ответ на тикет"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Ticket).where(Ticket.id == ticket_id)
            )
            ticket = result.scalar_one()
            
            ticket.is_answered = True
            ticket.answer = answer
            ticket.manager_chat_id = manager_chat_id
            ticket.answered_at = datetime.now(pytz.timezone('Europe/Moscow'))
            
            await session.commit()
            logger.info(f"Ticket {ticket_id} answered by manager {manager_chat_id}")
            return ticket
    
    async def is_manager(self, chat_id: int) -> bool:
        """Проверка, является ли пользователь менеджером"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Manager).where(Manager.chat_id == chat_id, Manager.is_active == True)
            )
            return result.scalar_one_or_none() is not None
    
    async def add_manager(self, chat_id: int, nickname: str) -> Manager:
        """Добавление менеджера"""
        async with self.async_session() as session:
            # Проверяем, существует ли уже менеджер
            existing_manager = await session.execute(
                select(Manager).where(Manager.chat_id == chat_id)
            )
            existing_manager = existing_manager.scalar_one_or_none()
            
            if existing_manager:
                # Если менеджер существует, активируем его
                existing_manager.is_active = True
                existing_manager.nickname = nickname
                manager = existing_manager
            else:
                # Создаем нового менеджера
                manager = Manager(chat_id=chat_id, nickname=nickname)
                session.add(manager)
            
            await session.commit()
            await session.refresh(manager)
            logger.info(f"Manager added/updated: {nickname} ({chat_id})")
            return manager
    
    async def remove_manager(self, chat_id: int) -> bool:
        """Удаление менеджера (деактивация)"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Manager).where(Manager.chat_id == chat_id)
            )
            manager = result.scalar_one_or_none()
            
            if manager:
                manager.is_active = False
                await session.commit()
                logger.info(f"Manager deactivated: {manager.nickname} ({chat_id})")
                return True
            return False
    
    async def get_all_managers(self) -> list[Manager]:
        """Получение списка всех активных менеджеров"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Manager).where(Manager.is_active == True).order_by(Manager.created_at)
            )
            return result.scalars().all()
    
    async def get_managers_for_notifications(self) -> list[Manager]:
        """Получение списка менеджеров для уведомлений"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Manager).where(Manager.is_active == True).order_by(Manager.created_at)
            )
            return result.scalars().all()
    
    async def get_manager_by_chat_id(self, chat_id: int) -> Manager:
        """Получение менеджера по chat_id"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Manager).where(Manager.chat_id == chat_id)
            )
            return result.scalar_one_or_none()
    
    async def get_manager_stats(self, manager_chat_id: int) -> dict:
        """Получение статистики менеджера"""
        async with self.async_session() as session:
            # Количество отвеченных тикетов
            result = await session.execute(
                select(Ticket).where(
                    Ticket.manager_chat_id == manager_chat_id,
                    Ticket.is_answered == True
                )
            )
            answered_tickets = result.scalars().all()
            
            return {
                'total_answered': len(answered_tickets),
                'last_activity': max([t.answered_at for t in answered_tickets]) if answered_tickets else None
            }
    
    async def get_tickets_count(self) -> dict:
        """Получение статистики по тикетам"""
        async with self.async_session() as session:
            # Все тикеты
            result_all = await session.execute(select(Ticket))
            all_tickets = result_all.scalars().all()
            
            # Неотвеченные тикеты
            result_pending = await session.execute(
                select(Ticket).where(Ticket.is_answered == False)
            )
            pending_tickets = result_pending.scalars().all()
            
            # Отвеченные тикеты
            result_answered = await session.execute(
                select(Ticket).where(Ticket.is_answered == True)
            )
            answered_tickets = result_answered.scalars().all()
            
            return {
                'total': len(all_tickets),
                'pending': len(pending_tickets),
                'answered': len(answered_tickets)
            }

db = Database()