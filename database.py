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
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    echo=False,
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
            # Si la conversación existe pero no tiene user_id y se proporciona uno, actualizarlo
            if conv.user_id is None and user_id is not None:
                conv.user_id = user_id
                db.commit()
                print(f"[DEBUG] Actualizado user_id={user_id} para conversation_id={conv.id}")
            else:
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


def migrate_conversations_with_user_id() -> int:
    """
    Migra las conversaciones antiguas extrayendo el user_id del session_id.
    Retorna la cantidad de conversaciones actualizadas.
    """
    import re
    db = get_session()
    try:
        # Buscar todas las conversaciones con user_id = NULL
        null_user_convs = (
            db.query(Conversation)
            .filter(Conversation.user_id == None)
            .all()
        )
        
        updated_count = 0
        for conv in null_user_convs:
            # Intentar extraer user_id de session_id con patrón mood_check_{user_id}_{timestamp}
            match = re.match(r'^mood_check_(\d+)_\d+$', conv.session_id)
            if match:
                conv.user_id = int(match.group(1))
                updated_count += 1
                print(f"[MIGRATE] conversation_id={conv.id} session_id={conv.session_id} -> user_id={conv.user_id}")
        
        if updated_count > 0:
            db.commit()
            print(f"[MIGRATE] {updated_count} conversaciones actualizadas")
        
        return updated_count
    except Exception as e:
        db.rollback()
        print(f"[MIGRATE] Error: {e}")
        return 0
    finally:
        db.close()

def get_user_conversations(user_id: int) -> list[dict]:
    """Devuelve el historial de sesiones de un usuario."""
    db = get_session()
    try:
        conversations = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )
        
        result = []
        for conv in conversations:
            # Obtener el primer mensaje del usuario como resumen/título
            first_msg = (
                db.query(Message)
                .filter(Message.conversation_id == conv.id, Message.role == "usuario")
                .order_by(Message.timestamp.asc())
                .first()
            )
            title = first_msg.content[:40] + "..." if first_msg and len(first_msg.content) > 40 else (first_msg.content if first_msg else "Nueva conversación")
            
            result.append({
                "session_id": conv.session_id,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "is_active": conv.is_active,
                "title": title
            })
        return result
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


def get_messages(session_id: str, limit: int = 50, include_inactive: bool = False) -> list[dict]:
    """Lista de mensajes de la sesión más reciente, ordenados cronológicamente."""
    db = get_session()
    try:
        # Subquery para obtener la conversación más reciente (activa o no según corresponda)
        conv_query = (
            db.query(Conversation.id)
            .filter(Conversation.session_id == session_id)
        )
        if not include_inactive:
            conv_query = conv_query.filter(Conversation.is_active == True)
        
        # Obtener el ID de la conversación más reciente
        latest_conv = conv_query.order_by(Conversation.updated_at.desc()).first()
        
        if not latest_conv:
            print(f"[DEBUG] No conversation found for session_id={session_id}, include_inactive={include_inactive}")
            return []
        
        # Obtener mensajes de esa conversación específica
        rows = (
            db.query(Message)
            .filter(Message.conversation_id == latest_conv[0])
            .order_by(Message.timestamp.asc())
            .limit(limit)
            .all()
        )

        print(f"[DEBUG] Found {len(rows)} messages for session_id={session_id}, conversation_id={latest_conv[0]}")

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
# Álbum (metadata ligera)
# ═══════════════════════════════════════════════════════════

def save_album_entry_metadata(
    user_id: int,
    session_id: str,
    diary_entry_id: int,
    entry_type: str = "texto",
    mood_tag: Optional[str] = None,
    is_synced: bool = True,
) -> int:
    """Guarda metadata ligera de una entrada de álbum y retorna su ID."""
    db = get_session()
    try:
        entry = AlbumEntry(
            user_id=user_id,
            session_id=session_id,
            diary_entry_id=diary_entry_id,
            entry_type=entry_type,
            mood_tag=mood_tag,
            is_synced=is_synced,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry.id
    finally:
        db.close()


def get_album_entries(user_id: int, limit: int = 50) -> list[dict]:
    """Obtiene las entradas de álbum de un usuario (metadata ligera)."""
    db = get_session()
    try:
        entries = (
            db.query(AlbumEntry)
            .filter(AlbumEntry.user_id == user_id)
            .order_by(AlbumEntry.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": entry.id,
                "diary_entry_id": entry.diary_entry_id,
                "entry_type": entry.entry_type,
                "mood_tag": entry.mood_tag,
                "is_synced": entry.is_synced,
                "created_at": entry.created_at.isoformat() if entry.created_at else "",
            }
            for entry in entries
        ]
    finally:
        db.close()


def delete_album_entry(entry_id: int) -> bool:
    """Elimina una entrada de álbum (solo metadata local)."""
    db = get_session()
    try:
        affected = (
            db.query(AlbumEntry)
            .filter(AlbumEntry.id == entry_id)
            .delete()
        )
        db.commit()
        return affected > 0
    finally:
        db.close()


def get_album_entry_by_diary_id(diary_entry_id: int) -> dict | None:
    """Obtiene la metadata local basada en el ID del microservicio de Diario."""
    db = get_session()
    try:
        entry = (
            db.query(AlbumEntry)
            .filter(AlbumEntry.diary_entry_id == diary_entry_id)
            .first()
        )
        
        if entry:
            return {
                "id": entry.id,
                "diary_entry_id": entry.diary_entry_id,
                "entry_type": entry.entry_type,
                "mood_tag": entry.mood_tag,
                "is_synced": entry.is_synced,
                "created_at": entry.created_at.isoformat() if entry.created_at else "",
            }
        return None
    finally:
        db.close()
