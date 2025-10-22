from datetime import datetime
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
import pytz

from database import db
from notifications import notification_manager

from config import config


logger = logging.getLogger(__name__)

manager_router = Router()


# Состояния для FSM
class ManagerStates(StatesGroup):
    waiting_for_manager_chat_id = State()
    waiting_for_manager_nickname = State()
    waiting_for_ticket_answer = State()


def get_main_keyboard():
    """Основная клавиатура для менеджера."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎫 Список тикетов", callback_data="show_tickets")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")],
            [InlineKeyboardButton(text="👥 Управление менеджерами", callback_data="manage_managers")],
            [InlineKeyboardButton(text="🆘 Помощь", callback_data="show_help")],
        ]
    )


def get_admin_keyboard():
    """Клавиатура для админа."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить менеджера", callback_data="add_manager")],
            [InlineKeyboardButton(text="🗑️ Удалить менеджера", callback_data="remove_manager")],
            [InlineKeyboardButton(text="📋 Список менеджеров", callback_data="list_managers")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")],
        ]
    )


def get_ticket_keyboard(ticket_id: int):
    """Создание клавиатуры для ответа на тикет."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Ответить", callback_data=f"answer_{ticket_id}")],
            [InlineKeyboardButton(text="❌ Закрыть без ответа", callback_data=f"close_{ticket_id}")],
        ]
    )


def is_admin(chat_id: int) -> bool:
    """Проверка, является ли пользователь админом."""
    return chat_id in config.ADMIN_CHAT_IDS


@manager_router.message(Command("start"))
async def start_command(message: Message):
    """Обработчик команды /start для менеджера."""
    if not await db.is_manager(message.chat.id) and not is_admin(message.chat.id):
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    welcome_text = """
👨‍💼 Панель менеджера поддержки

Используйте кнопки ниже для управления:
• 🎫 Список тикетов - показать неотвеченные вопросы от клиентов
• 📊 Статистика - показать статистику
• 👥 Управление менеджерами - управление доступом (только для админов)
• 🆘 Помощь - показать справку

🚨 Вы будете получать уведомления о новых тикетах от клиентов!
    """
    await message.answer(welcome_text, reply_markup=get_main_keyboard())


@manager_router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню."""
    await callback.message.edit_text("👨‍💼 Панель менеджера поддержки", reply_markup=get_main_keyboard())
    await callback.answer()


@manager_router.callback_query(F.data == "show_tickets")
async def show_tickets(callback: CallbackQuery):
    """Показать список тикетов."""
    if not await db.is_manager(callback.message.chat.id) and not is_admin(callback.message.chat.id):
        await callback.answer("❌ Доступ запрещен")
        return

    try:
        tickets = await db.get_pending_tickets()

        if not tickets:
            await callback.message.edit_text(
                "🎉 На данный момент нет неотвеченных тикетов!", reply_markup=get_main_keyboard()
            )
            await callback.answer()
            return

        text = f"📋 Неотвеченные тикеты ({len(tickets)}):\n\n"
        await callback.message.edit_text(text, reply_markup=get_main_keyboard())

        # Отправляем каждый тикет отдельным сообщением
        for ticket in tickets:
            ticket_text = f"""
👤 Клиент: {ticket.client_nickname}
🆔 ID тикета: #{ticket.id}
⏰ Время: {ticket.created_at.strftime("%d.%m.%Y %H:%M")}
💬 Вопрос:
{ticket.question[:500]}{"..." if len(ticket.question) > 500 else ""}
            """

            await callback.message.answer(ticket_text, reply_markup=get_ticket_keyboard(ticket.id))

        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing tickets: {e}")
        await callback.answer("❌ Ошибка при загрузке тикетов")


@manager_router.callback_query(F.data == "show_stats")
async def show_stats(callback: CallbackQuery):
    """Показать статистику."""
    if not await db.is_manager(callback.message.chat.id) and not is_admin(callback.message.chat.id):
        await callback.answer("❌ Доступ запрещен")
        return

    try:
        tickets_stats = await db.get_tickets_count()
        managers = await db.get_all_managers()

        stats_text = f"""
📊 СТАТИСТИКА СИСТЕМЫ

📈 Тикеты:
   • Всего: {tickets_stats["total"]}
   • Ожидают ответа: {tickets_stats["pending"]}
   • Отвечено: {tickets_stats["answered"]}

👥 Активных менеджеров: {len(managers)}
⏰ Обновлено: {datetime.now(pytz.timezone(config.TIMEZONE)).strftime("%H:%M %d.%m.%Y")}
        """

        await callback.message.edit_text(stats_text, reply_markup=get_main_keyboard())
        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing stats: {e}")
        await callback.answer("❌ Ошибка при загрузке статистики")


@manager_router.callback_query(F.data == "manage_managers")
async def manage_managers(callback: CallbackQuery):
    """Управление менеджерами (только для админов)."""
    if not is_admin(callback.message.chat.id):
        await callback.answer("❌ Эта функция доступна только администраторам")
        return

    managers_text = """
👥 Управление менеджерами

Здесь вы можете:
• Добавить нового менеджера
• Удалить существующего менеджера
• Просмотреть список всех менеджеров
    """
    await callback.message.edit_text(managers_text, reply_markup=get_admin_keyboard())
    await callback.answer()


@manager_router.callback_query(F.data == "add_manager")
async def add_manager_start(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления менеджера."""
    if not is_admin(callback.message.chat.id):
        await callback.answer("❌ Доступ запрещен")
        return

    await state.set_state(ManagerStates.waiting_for_manager_chat_id)
    await callback.message.edit_text(
        "✍️ Введите chat_id пользователя, которого хотите добавить как менеджера:\n\n"
        "Chat_id можно получить переслав сообщение пользователя боту @userinfobot",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_add_manager")]]
        ),
    )
    await callback.answer()


@manager_router.callback_query(F.data == "cancel_add_manager")
async def cancel_add_manager(callback: CallbackQuery, state: FSMContext):
    """Отмена добавления менеджера."""
    await state.clear()
    await callback.message.edit_text("❌ Добавление менеджера отменено", reply_markup=get_admin_keyboard())
    await callback.answer()


@manager_router.message(ManagerStates.waiting_for_manager_chat_id)
async def process_manager_chat_id(message: Message, state: FSMContext):
    """Обработка chat_id менеджера."""
    try:
        chat_id = int(message.text.strip())

        # Проверяем, не является ли пользователь уже менеджером
        existing_manager = await db.get_manager_by_chat_id(chat_id)
        if existing_manager and existing_manager.is_active:
            await message.answer(
                f"❌ Пользователь с chat_id {chat_id} уже является менеджером", reply_markup=get_admin_keyboard()
            )
            await state.clear()
            return

        # Сохраняем chat_id и запрашиваем никнейм
        await state.update_data(manager_chat_id=chat_id)
        await state.set_state(ManagerStates.waiting_for_manager_nickname)

        await message.answer(
            "✅ Chat_id принят. Теперь введите никнейм или имя для этого менеджера:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_add_manager")]]
            ),
        )

    except ValueError:
        await message.answer("❌ Неверный формат chat_id. Введите числовой chat_id:")


@manager_router.message(ManagerStates.waiting_for_manager_nickname)
async def process_manager_nickname(message: Message, state: FSMContext):
    """Обработка никнейма менеджера."""
    nickname = message.text.strip()

    if len(nickname) < 2 or len(nickname) > 100:
        await message.answer("❌ Никнейм должен быть от 2 до 100 символов. Введите снова:")
        return

    # Получаем сохраненный chat_id
    data = await state.get_data()
    chat_id = data["manager_chat_id"]

    try:
        # Добавляем менеджера в базу
        manager = await db.add_manager(chat_id, nickname)

        success_text = f"""
✅ Менеджер успешно добавлен!

👤 Имя: {manager.nickname}
🆔 Chat ID: {manager.chat_id}
📅 Добавлен: {manager.created_at.strftime("%d.%m.%Y %H:%M")}

Теперь пользователь имеет доступ к боту менеджера.
        """

        await message.answer(success_text, reply_markup=get_admin_keyboard())

        # Пытаемся уведомить нового менеджера
        try:
            manager_bot = Bot(token=config.MANAGER_BOT_TOKEN)
            await manager_bot.send_message(
                chat_id=chat_id,
                text="🎉 Вас добавили как менеджера поддержки!\n\nИспользуйте команду /start для начала работы.",
            )
            await manager_bot.session.close()
        except Exception as e:
            logger.warning(f"Could not notify new manager: {e}")

    except Exception as e:
        logger.error(f"Error adding manager: {e}")
        await message.answer("❌ Ошибка при добавлении менеджера", reply_markup=get_admin_keyboard())

    await state.clear()


@manager_router.callback_query(F.data == "list_managers")
async def list_managers(callback: CallbackQuery):
    """Показать список всех менеджеров."""
    if not is_admin(callback.message.chat.id):
        await callback.answer("❌ Доступ запрещен")
        return

    try:
        managers = await db.get_all_managers()

        if not managers:
            await callback.message.edit_text("📭 Список менеджеров пуст", reply_markup=get_admin_keyboard())
            await callback.answer()
            return

        managers_text = "👥 Список активных менеджеров:\n\n"

        for i, manager in enumerate(managers, 1):
            stats = await db.get_manager_stats(manager.chat_id)
            last_activity = (
                stats["last_activity"].strftime("%d.%m.%Y %H:%M") if stats["last_activity"] else "Нет активности"
            )

            managers_text += f"{i}. 👤 {manager.nickname}\n"
            managers_text += f"   🆔 ID: {manager.chat_id}\n"
            managers_text += f"   📊 Отвечено тикетов: {stats['total_answered']}\n"
            managers_text += f"   ⏰ Последняя активность: {last_activity}\n"
            managers_text += f"   📅 Добавлен: {manager.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"

        await callback.message.edit_text(managers_text, reply_markup=get_admin_keyboard())
        await callback.answer()

    except Exception as e:
        logger.error(f"Error listing managers: {e}")
        await callback.answer("❌ Ошибка при загрузке списка менеджеров")


@manager_router.callback_query(F.data == "remove_manager")
async def remove_manager_start(callback: CallbackQuery):
    """Начало процесса удаления менеджера."""
    if not is_admin(callback.message.chat.id):
        await callback.answer("❌ Доступ запрещен")
        return

    try:
        managers = await db.get_all_managers()

        if not managers:
            await callback.message.edit_text(
                "📭 Нет активных менеджеров для удаления", reply_markup=get_admin_keyboard()
            )
            await callback.answer()
            return

        # Создаем клавиатуру с менеджерами для удаления
        keyboard = []
        for manager in managers:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"🗑️ {manager.nickname} (ID: {manager.chat_id})",
                        callback_data=f"remove_manager_{manager.chat_id}",
                    )
                ]
            )

        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="manage_managers")])

        await callback.message.edit_text(
            "🗑️ Выберите менеджера для удаления:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error starting manager removal: {e}")
        await callback.answer("❌ Ошибка при загрузке менеджеров")


@manager_router.callback_query(F.data.startswith("remove_manager_"))
async def remove_manager_confirm(callback: CallbackQuery):
    """Подтверждение удаления менеджера."""
    if not is_admin(callback.message.chat.id):
        await callback.answer("❌ Доступ запрещен")
        return

    manager_chat_id = int(callback.data.split("_")[2])
    manager = await db.get_manager_by_chat_id(manager_chat_id)

    if not manager:
        await callback.answer("❌ Менеджер не найден")
        return

    confirmation_text = f"""
⚠️ Подтверждение удаления

Вы уверены, что хотите удалить менеджера?
👤 Имя: {manager.nickname}
🆔 Chat ID: {manager.chat_id}
📅 В команде с: {manager.created_at.strftime("%d.%m.%Y %H:%M")}

Менеджер потеряет доступ к боту.
    """

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_remove_{manager.chat_id}"),
                InlineKeyboardButton(text="❌ Нет, отмена", callback_data="manage_managers"),
            ]
        ]
    )

    await callback.message.edit_text(confirmation_text, reply_markup=keyboard)
    await callback.answer()


@manager_router.callback_query(F.data.startswith("confirm_remove_"))
async def remove_manager_execute(callback: CallbackQuery):
    """Выполнение удаления менеджера."""
    if not is_admin(callback.message.chat.id):
        await callback.answer("❌ Доступ запрещен")
        return

    manager_chat_id = int(callback.data.split("_")[2])
    manager = await db.get_manager_by_chat_id(manager_chat_id)

    if not manager:
        await callback.answer("❌ Менеджер не найден")
        return

    try:
        success = await db.remove_manager(manager_chat_id)

        if success:
            await callback.message.edit_text(
                f"✅ Менеджер {manager.nickname} успешно удален", reply_markup=get_admin_keyboard()
            )

            # Уведомляем удаленного менеджера
            try:
                manager_bot = Bot(token=config.MANAGER_BOT_TOKEN)
                await manager_bot.send_message(
                    chat_id=manager_chat_id, text="❌ Ваш доступ к боту менеджера был отозван."
                )
                await manager_bot.session.close()
            except Exception as e:
                logger.warning(f"Could not notify removed manager: {e}")

        else:
            await callback.message.edit_text("❌ Ошибка при удалении менеджера", reply_markup=get_admin_keyboard())

    except Exception as e:
        logger.error(f"Error removing manager: {e}")
        await callback.message.edit_text("❌ Ошибка при удалении менеджера", reply_markup=get_admin_keyboard())

    await callback.answer()


@manager_router.message(F.text)
async def handle_manager_message(message: Message, state: FSMContext):
    """Обработка сообщений от менеджера."""
    if not await db.is_manager(message.chat.id) and not is_admin(message.chat.id):
        return

    # Проверяем, находится ли менеджер в режиме ответа на тикет
    current_state = await state.get_state()
    if current_state == ManagerStates.waiting_for_ticket_answer:
        data = await state.get_data()
        ticket_id = data.get("ticket_id")

        try:
            # Отвечаем на тикет
            ticket = await db.answer_ticket(ticket_id=ticket_id, answer=message.text, manager_chat_id=message.chat.id)

            # Очищаем состояние
            await state.clear()

            await message.answer(f"✅ Ответ на тикет #{ticket_id} отправлен клиенту!", reply_markup=get_main_keyboard())

        except Exception as e:
            logger.error(f"Error answering ticket: {e}")
            await message.answer("❌ Ошибка при отправке ответа")


@manager_router.callback_query(F.data.startswith("answer_"))
async def start_answer(callback: CallbackQuery, state: FSMContext):
    """Начало процесса ответа на тикет."""
    if not await db.is_manager(callback.message.chat.id):
        await callback.answer("❌ Доступ запрещен")
        return

    ticket_id = int(callback.data.split("_")[1])
    await state.set_state(ManagerStates.waiting_for_ticket_answer)
    await state.update_data(ticket_id=ticket_id)

    ticket = await db.get_ticket_by_id(ticket_id)
    if not ticket:
        await callback.answer("❌ Тикет не найден")
        return

    await callback.message.answer(
        f"✍️ Введите ответ для тикета #{ticket_id}:\n\n"
        f"Клиент: {ticket.client_nickname}\n"
        f"Вопрос: {ticket.question[:200]}..."
    )
    await callback.answer()


@manager_router.callback_query(F.data.startswith("close_"))
async def close_ticket(callback: CallbackQuery):
    """Закрытие тикета без ответа."""
    if not await db.is_manager(callback.message.chat.id):
        await callback.answer("❌ Доступ запрещен")
        return

    ticket_id = int(callback.data.split("_")[1])

    try:
        ticket = await db.answer_ticket(
            ticket_id=ticket_id, answer="Тикет закрыт без ответа", manager_chat_id=callback.message.chat.id
        )

        await callback.message.edit_text(f"✅ Тикет #{ticket_id} закрыт без ответа", reply_markup=None)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error closing ticket: {e}")
        await callback.answer("❌ Ошибка при закрытии тикета")


@manager_router.callback_query(F.data == "show_help")
async def show_help(callback: CallbackQuery):
    """Показать справку для менеджера."""
    help_text = """
🆘 Справка для менеджера

🎫 Список тикетов - показать все неотвеченные вопросы от клиентов
📊 Статистика - показать статистику тикетов
👥 Управление менеджерами - управление доступом (только для админов)

📝 Как ответить на тикет:
1. Нажмите "🎫 Список тикетов"
2. Выберите тикет и нажмите "📝 Ответить" 
3. Введите текст ответа
4. Ответ автоматически отправится клиенту через n8n

❌ Закрыть без ответа - закрыть тикет без отправки ответа клиенту

🚨 Вы будете получать уведомления о новых тикетах!
    """
    await callback.message.edit_text(help_text, reply_markup=get_main_keyboard())
    await callback.answer()


async def run_manager_bot():
    """Запуск бота для менеджеров."""
    # Инициализируем менеджер уведомлений
    await notification_manager.initialize()

    bot = Bot(token=config.MANAGER_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(manager_router)

    await dp.start_polling(bot)
