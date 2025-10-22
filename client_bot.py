import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message

from database import db
from notifications import notification_manager

from config import config


logger = logging.getLogger(__name__)

client_router = Router()


@client_router.message(Command("start"))
async def start_command(message: Message):
    """Обработчик команды /start."""
    welcome_text = """
🤖 Добро пожаловать в службу поддержки!

Просто напишите ваш вопрос, и наши менеджеры скоро свяжутся с вами.

Мы постараемся ответить как можно скорее! ⏱️
    """
    await message.answer(welcome_text)


@client_router.message(Command("help"))
async def help_command(message: Message):
    """Обработчик команды /help."""
    help_text = """
📋 Доступные команды:
/start - Начать работу с ботом
/help - Получить справку
/status - Проверить статус ваших вопросов

Просто напишите ваш вопрос в чат, и мы на него ответим!
    """
    await message.answer(help_text)


@client_router.message(Command("status"))
async def status_command(message: Message):
    """Проверка статуса вопросов пользователя."""
    status_text = """
📊 Для проверки статуса ваших вопросов свяжитесь с менеджерами.

Ваши вопросы находятся в обработке, скоро мы вам ответим!
    """
    await message.answer(status_text)


@client_router.message(F.text)
async def handle_question(message: Message):
    """Обработка вопросов от клиентов."""
    try:
        if len(message.text) > config.MAX_TICKET_LENGTH:
            await message.answer(
                f"❌ Ваш вопрос слишком длинный. Максимальная длина: {config.MAX_TICKET_LENGTH} символов."
            )
            return

        # Получаем никнейм пользователя
        nickname = message.from_user.username
        if not nickname:
            nickname = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
            if not nickname:
                nickname = "Анонимный пользователь"

        # Создаем тикет
        ticket = await db.create_ticket(client_chat_id=message.chat.id, client_nickname=nickname, question=message.text)

        # Отправляем подтверждение
        confirmation_text = f"""
✅ Ваш вопрос принят! Номер заявки: #{ticket.id}

Мы получили ваш вопрос и скоро на него ответим. Ожидайте, пожалуйста.

Ваш вопрос:
{message.text}
        """
        await message.answer(confirmation_text)

        logger.info(f"New question from {nickname}: {message.text[:50]}...")

        # Отправляем уведомления менеджерам
        asyncio.create_task(notification_manager.notify_new_ticket(ticket))

    except Exception as e:
        logger.error(f"Error handling question: {e}")
        await message.answer("❌ Произошла ошибка при обработке вашего вопроса. Пожалуйста, попробуйте позже.")


async def run_client_bot():
    """Запуск клиентского бота."""
    bot = Bot(token=config.CLIENT_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(client_router)

    await dp.start_polling(bot)
