"""
Sanity Agent – Tool: Album
Guarda y elimina entradas del álbum en el microservicio de Diario.
El agente solo guarda metadata ligera localmente para contexto terapéutico.
"""

from __future__ import annotations

import os
from datetime import datetime

import httpx
from langchain_core.tools import tool

from database import (
    save_album_entry_metadata,
    get_album_entries,
    delete_album_entry as delete_local_album_entry,
)

DIARY_SERVICE_URL = os.getenv("DIARY_SERVICE_URL", "http://localhost:8083")


@tool
def save_to_album(
    user_id: int,
    session_id: str,
    content: str,
    entry_type: str = "texto",
    image_url: str = "",
    mood_tag: str = "",
) -> str:
    """
    Guarda un mensaje, reflexión o foto en el álbum personal del usuario.
    El contenido real se guarda en el microservicio de Diario.
    El agente solo guarda metadata ligera para contexto terapéutico.
    
    Usa esta herramienta cuando el usuario quiera guardar:
    - Una reflexión significativa
    - Un momento especial
    - Un logro personal
    - Una foto con significado emocional

    Args:
        user_id: ID del usuario.
        session_id: ID de la sesión actual.
        content: Texto del mensaje, reflexión o descripción.
        entry_type: Tipo de entrada: 'texto', 'foto', 'momento', 'reflexion', 'logro'.
        image_url: URL de la imagen si es una foto (opcional).
        mood_tag: Emoción asociada (ansiedad, felicidad, tristeza, etc.).
    
    Returns:
        Mensaje de confirmación o error.
    """
    try:
        # 1. Guardar en el microservicio de Diario (fuente de verdad)
        diary_entry_id = None
        synced = False
        
        try:
            payload = {
                "usuarioId": user_id,
                "contenido": content,
                "tipoEntrada": entry_type,
            }
            if image_url:
                payload["imagenUrl"] = image_url
            
            response = httpx.post(
                f"{DIARY_SERVICE_URL}/api/diary/entradas",
                json=payload,
                timeout=10.0,
            )
            
            if response.status_code < 400:
                synced = True
                # Extraer el ID de la entrada creada
                try:
                    diary_entry_id = response.json().get("id") or response.json().get("idEntrada")
                except Exception:
                    diary_entry_id = None
            else:
                return f"❌ Error al guardar en el álbum: Servicio de Diario respondió con estado {response.status_code}"
                
        except httpx.TimeoutException:
            return "❌ Error al guardar en el álbum: El servicio de Diario no responde. Inténtalo de nuevo más tarde."
        except Exception as e:
            return f"❌ Error al guardar en el álbum: {str(e)}"
        
        # 2. Guardar metadata ligera localmente (para contexto terapéutico)
        local_entry_id = save_album_entry_metadata(
            user_id=user_id,
            session_id=session_id,
            diary_entry_id=diary_entry_id,
            entry_type=entry_type,
            mood_tag=mood_tag if mood_tag else None,
            is_synced=synced,
        )
        
        sync_msg = "✅ y sincronizado con tu Diario" if synced else "⚠️ (no se pudo sincronizar con Diario)"
        
        return (
            f"✨ Guardado exitosamente en tu álbum {sync_msg}.\n"
            f"   Tipo: {entry_type}\n"
            f"   Reflexión: {content[:80]}{'...' if len(content) > 80 else ''}\n"
            f"   ID local: {local_entry_id}"
        )

    except Exception as e:
        return f"❌ Error al guardar en el álbum: {str(e)}"


@tool
def delete_from_album(user_id: int, diary_entry_id: int) -> str:
    """
    Elimina una entrada del álbum del usuario.
    Primero elimina del microservicio de Diario, luego la metadata local.
    
    Usa esta herramienta cuando el usuario quiera eliminar una entrada específica
    de su álbum.

    Args:
        user_id: ID del usuario.
        diary_entry_id: ID de la entrada en el microservicio de Diario.
    
    Returns:
        Mensaje de confirmación o error.
    """
    try:
        # 1. Eliminar del microservicio de Diario
        deleted_from_diary = False
        try:
            response = httpx.delete(
                f"{DIARY_SERVICE_URL}/api/diary/entradas/{diary_entry_id}",
                timeout=10.0,
            )
            if response.status_code < 400:
                deleted_from_diary = True
        except Exception:
            pass  # Continuar aunque falle el servicio de Diario
        
        # 2. Eliminar metadata local (si existe)
        deleted_locally = False
        local_entry = get_album_entry_by_diary_id(diary_entry_id)
        if local_entry:
            deleted_locally = delete_local_album_entry(local_entry["id"])
        
        if deleted_from_diary:
            return f"✅ Entrada eliminada exitosamente de tu álbum."
        elif deleted_locally:
            return f"⚠️ Entrada eliminada del registro local, pero no se pudo eliminar del Diario (el servicio puede estar fuera de línea)."
        else:
            return f"❌ No se pudo eliminar la entrada. Verifica que el ID sea correcto."
            
    except Exception as e:
        return f"❌ Error al eliminar del álbum: {str(e)}"


@tool
def list_album_entries(user_id: int, limit: int = 20) -> str:
    """
    Lista las entradas del álbum de un usuario.
    Muestra la metadata ligera almacenada localmente.
    
    Usa esta herramienta cuando el usuario quiera ver su historial de entradas
    o cuando preguntes por reflexiones guardadas anteriormente.

    Args:
        user_id: ID del usuario.
        limit: Máximo número de entradas a retornar (default: 20).
    
    Returns:
        Lista de entradas con metadata (tipo, emoción, fecha).
    """
    try:
        entries = get_album_entries(user_id, limit)
        
        if not entries:
            return "El usuario aún no tiene entradas guardadas en su álbum."
        
        lines = [f"📔 Álbum de {user_id} ({len(entries)} entradas):\n"]
        
        for entry in entries:
            emoji = {
                "texto": "📝",
                "foto": "📷",
                "momento": "✨",
                "reflexion": "💭",
                "logro": "🏆",
            }.get(entry["entry_type"], "📌")
            
            mood_emoji = {
                "ansiedad": "😰",
                "tristeza": "😔",
                "felicidad": "😊",
                "calma": "😌",
                "neutral": "😐",
            }.get(entry.get("mood_tag", ""), "")
            
            sync_status = "✅" if entry["is_synced"] else "⚠️"
            
            lines.append(
                f"  {emoji} {mood_emoji} [{entry['entry_type']}]"
                f" {entry['created_at'][:10]} {sync_status}"
            )
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"Error al listar entradas del álbum: {str(e)}"
