from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import pytz


Base = declarative_base()


class Ticket(Base):
    __tablename__ = 'tickets'
    
    id = Column(Integer, primary_key=True)
    client_chat_id = Column(Integer, nullable=False)
    client_nickname = Column(String(100), nullable=False)
    question = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Europe/Moscow')))
    is_answered = Column(Boolean, default=False)
    answer = Column(Text, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    manager_chat_id = Column(Integer, nullable=True)


class Manager(Base):
    __tablename__ = 'managers'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True, nullable=False)
    nickname = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Europe/Moscow')))