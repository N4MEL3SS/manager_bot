from datetime import datetime

import pytz
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    client_chat_id = Column(Integer, nullable=False)
    client_nickname = Column(String(100), nullable=False)
    question = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone("Europe/Moscow")))
    is_answered = Column(Boolean, default=False)
    answer = Column(Text, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    manager_chat_id = Column(Integer, nullable=True)

    # Поля для интеграции с n8n
    source = Column(String(50), default="n8n_ai")
    external_id = Column(String(100), nullable=True)
    ai_processed = Column(Boolean, default=True)
    ai_confident = Column(Boolean, default=False)


class Manager(Base):
    __tablename__ = "managers"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True, nullable=False)
    nickname = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone("Europe/Moscow")))
