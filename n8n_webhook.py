import logging

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database import db
from notifications import notification_manager

from config import config


logger = logging.getLogger(__name__)

app = FastAPI(title="N8N Webhook for AI Ticket System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def verify_webhook(authorization: str | None = Header(None)):
    """Проверка авторизации для webhook."""
    if config.N8N_API_KEY and (not authorization or authorization != f"Bearer {config.N8N_API_KEY}"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


@app.post("/webhook/ticket")
async def create_ticket_from_n8n_ai(data: dict, authorized: bool = Depends(verify_webhook)):
    """Webhook для создания тикетов из n8n после AI обработки.

    Ожидаемые поля в data:
    - chat_id: ID чата клиента (обязательно)
    - username: имя пользователя
    - question: вопрос клиента (обязательно)
    - ai_confident: нашел ли AI ответ в БЗ (обязательно)
    - external_id: внешний ID (опционально)
    """
    try:
        logger.info(f"Received ticket from n8n AI: {data}")

        # Валидация обязательных полей
        required_fields = ["chat_id", "question", "ai_confident"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        # Создаем тикет только если AI не нашел ответ
        if not data["ai_confident"]:
            ticket = await db.create_ticket_from_n8n(data)

            # Отправляем уведомления менеджерам
            await notification_manager.notify_new_ticket(ticket)

            return {"status": "success", "ticket_id": ticket.id, "message": "Ticket created and managers notified"}
        else:
            return {"status": "success", "message": "AI handled the question, no ticket created"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ticket from n8n AI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "n8n_ai_webhook"}


async def run_n8n_webhook():
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
