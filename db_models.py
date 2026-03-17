"""
Sanity Agent – SQLAlchemy ORM Models
Modelos ORM que crean las tablas automáticamente (como Hibernate ddl-auto=update).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker


# ═══════════════════════════════════════════════════════════
# Base declarativa (equivalente a @Entity en JPA)
# ═══════════════════════════════════════════════════════════

class Base(DeclarativeBase):
    pass


# ═══════════════════════════════════════════════════════════
# Tabla: agent_conversations (sesiones de chat)
# ═══════════════════════════════════════════════════════════

class Conversation(Base):
    __tablename__ = "agent_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relación uno-a-muchos con mensajes (como @OneToMany en JPA)
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


# ═══════════════════════════════════════════════════════════
# Tabla: agent_messages (mensajes del chat)
# ═══════════════════════════════════════════════════════════

class Message(Base):
    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)          # 'usuario' | 'asistente'
    content = Column(Text, nullable=False)
    emotions = Column(String(500), nullable=True)       # JSON array de emociones
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relación muchos-a-uno (como @ManyToOne en JPA)
    conversation = relationship("Conversation", back_populates="messages")


# ═══════════════════════════════════════════════════════════
# Tabla: agent_reminders (recordatorios de hábitos saludables)
# ═══════════════════════════════════════════════════════════

class Reminder(Base):
    __tablename__ = "agent_reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String(255), nullable=False)
    habit_name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    frequency = Column(String(50), nullable=False, default="diario")
    reminder_time = Column(String(10), nullable=True)   # HH:MM
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# Tabla: agent_album_entries (metadata ligera de álbum desde el chat)
# ═══════════════════════════════════════════════════════════

class AlbumEntry(Base):
    __tablename__ = "agent_album_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String(255), nullable=False)
    diary_entry_id = Column(Integer, nullable=True)  # ID en el microservicio de Diario
    entry_type = Column(String(50), nullable=False, default="texto")
    mood_tag = Column(String(50), nullable=True)     # Emoción asociada (ansiedad, felicidad, etc.)
    is_synced = Column(Boolean, nullable=False, default=False)  # Si está sincronizado con Diario
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
