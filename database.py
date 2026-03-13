"""
Sanity Agent – Database Module (SQLAlchemy ORM)
Crea las tablas automáticamente como Hibernate (ddl-auto=update).
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

from db_models import Base, Conversation, Message, Reminder, AlbumEntry


# ═══════════════════════════════════════════════════════════
# Conexión con SQLAlchemy (como spring.datasource en Spring)
# ═══════════════════════════════════════════════════════════

CONNECTION_STRING = os.getenv("AZURE_SQL_CONNECTION_STRING", "")

# Convertir el connection string de ODBC a formato SQLAlchemy
# SQLAlchemy usa: mssql+pyodbc:///?odbc_connect=<connection_string>
SQLALCHEMY_URL = f"mssql+pyodbc:///?odbc_connect={CONNECTION_STRING}"

engine = create_engine(
    SQLALCHEMY_URL,
    echo=False,       # Poner True para ver las queries SQL (como spring.jpa.show-sql=true)
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Session:
    """Obtiene una sesión de base de datos (equivalente a EntityManager en JPA)."""
    return SessionLocal()


def init_db() -> None:
    """
    Crea todas las tablas automáticamente basándose en los modelos ORM.
    Equivalente a: spring.jpa.hibernate.ddl-auto=update
    
    - Si la tabla NO existe → la crea
    - Si la tabla YA existe → no la modifica (usa checkfirst=True)
    """
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("✅ Base de datos inicializada – tablas creadas/verificadas automáticamente.")


# ═══════════════════════════════════════════════════════════
# Conversaciones
# ═══════════════════════════════════════════════════════════

def get_or_create_conversation(session_id: str, user_id: Optional[int] = None) -> int:
    """Busca una conversación activa o crea una nueva. Retorna el ID."""
    db = get_session()
    try:
        conv = (
            db.query(Conversation)
            .filter(Conversation.session_id == session_id, Conversation.is_active == True)
            .order_by(Conversation.created_at.desc())
            .first()
        )

        if conv:
            conv.updated_at = datetime.utcnow()
            db.commit()
            return conv.id
        else:
            new_conv = Conversation(session_id=session_id, user_id=user_id)
            db.add(new_conv)
            db.commit()
            db.refresh(new_conv)
            return new_conv.id
    finally:
        db.close()


def deactivate_conversation(session_id: str) -> bool:
    """Desactiva todas las conversaciones de una sesión."""
    db = get_session()
    try:
        affected = (
            db.query(Conversation)
            .filter(Conversation.session_id == session_id)
            .update({"is_active": False})
        )
        db.commit()
        return affected > 0
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Mensajes
# ═══════════════════════════════════════════════════════════

def save_message(
    conversation_id: int,
    role: str,
    content: str,
    emotions: Optional[list[str]] = None,
) -> int:
    """Guarda un mensaje y retorna su ID."""
    db = get_session()
    try:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            emotions=json.dumps(emotions) if emotions else None,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg.id
    finally:
        db.close()


def get_messages(session_id: str, limit: int = 50) -> list[dict]:
    """Lista de mensajes de la sesión más reciente, ordenados cronológicamente."""
    db = get_session()
    try:
        rows = (
            db.query(Message)
            .join(Conversation)
            .filter(Conversation.session_id == session_id, Conversation.is_active == True)
            .order_by(Message.timestamp.asc())
            .limit(limit)
            .all()
        )

        result = []
        for msg in rows:
            emotions = []
            if msg.emotions:
                try:
                    emotions = json.loads(msg.emotions)
                except json.JSONDecodeError:
                    pass
            result.append({
                "rol": msg.role,
                "mensaje": msg.content,
                "emociones": emotions,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else "",
            })
        return result
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Recordatorios
# ═══════════════════════════════════════════════════════════

def create_reminder(
    user_id: int,
    session_id: str,
    habit_name: str,
    description: Optional[str] = None,
    frequency: str = "diario",
    reminder_time: Optional[str] = None,
) -> int:
    """Crea un recordatorio y retorna su ID."""
    db = get_session()
    try:
        rem = Reminder(
            user_id=user_id,
            session_id=session_id,
            habit_name=habit_name,
            description=description,
            frequency=frequency,
            reminder_time=reminder_time,
        )
        db.add(rem)
        db.commit()
        db.refresh(rem)
        return rem.id
    finally:
        db.close()


def get_reminders(user_id: int, only_active: bool = True) -> list[dict]:
    """Obtiene los recordatorios del usuario."""
    db = get_session()
    try:
        query = db.query(Reminder).filter(Reminder.user_id == user_id)
        if only_active:
            query = query.filter(Reminder.is_active == True)
        rows = query.order_by(Reminder.created_at.desc()).all()

        return [
            {
                "id": rem.id,
                "habit_name": rem.habit_name,
                "description": rem.description,
                "frequency": rem.frequency,
                "reminder_time": rem.reminder_time,
                "is_active": rem.is_active,
                "created_at": rem.created_at.isoformat() if rem.created_at else "",
            }
            for rem in rows
        ]
    finally:
        db.close()


def deactivate_reminder(reminder_id: int) -> bool:
    """Desactiva un recordatorio."""
    db = get_session()
    try:
        affected = (
            db.query(Reminder)
            .filter(Reminder.id == reminder_id)
            .update({"is_active": False})
        )
        db.commit()
        return affected > 0
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# Álbum
# ═══════════════════════════════════════════════════════════

def save_album_entry(
    user_id: int,
    session_id: str,
    content: Optional[str] = None,
    image_url: Optional[str] = None,
    entry_type: str = "texto",
) -> int:
    """Guarda una entrada de álbum y retorna su ID."""
    db = get_session()
    try:
        entry = AlbumEntry(
            user_id=user_id,
            session_id=session_id,
            content=content,
            image_url=image_url,
            entry_type=entry_type,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry.id
    finally:
        db.close()
