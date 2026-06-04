# models.py (упрощенная версия)
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    full_name = Column(String(200))
    reminder_time = Column(String(5), default='20:00')
    created_at = Column(DateTime, default=datetime.now)
    entries = relationship("Entry", back_populates="user", cascade="all, delete-orphan")


class Entry(Base):
    __tablename__ = 'entries'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    date = Column(DateTime, default=datetime.now)
    situation = Column(Text)
    automatic_thought = Column(Text)
    rational_response = Column(Text)
    result = Column(Text)
    status = Column(String(20), default='draft')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    user = relationship("User", back_populates="entries")
    emotions = relationship("EntryEmotion", back_populates="entry", cascade="all, delete-orphan")


class EntryEmotion(Base):
    __tablename__ = "entry_emotions"
    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("entries.id", ondelete="CASCADE"))
    emotion_name = Column(String)
    intensity = Column(Integer)
    reassessment_intensity = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    entry = relationship("Entry", back_populates="emotions")
