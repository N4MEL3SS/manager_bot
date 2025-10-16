# manager_bot

Для запуска бота выполните следующие шаги:
0. Установите Python3.13 или выше если он не установлен.
1. Выполните команду `pip install -r requirements.txt` для установки всех зависимостей.
2. Создайте в корне проекта файл **.env** и укажите в нём следующие данные:
    ```
    CLIENT_BOT_TOKEN=<client_bot_token>
    MANAGER_BOT_TOKEN=<manager_bot_token>

    DATABASE_URL=sqlite+aiosqlite:///tickets.db

    # Используйте @userinfobot для получения chat_id
    ADMIN_CHAT_IDS=<your_telegram_chat_id> 

    # Настройки уведомлений
    NOTIFY_MANAGERS_NEW_TICKETS=True
    NOTIFICATION_COOLDOWN=30
    ```
3. Запустите ботов командой `python main.py`
