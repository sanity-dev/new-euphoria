"""
Sanity Agent – Tool: Album
Guarda mensajes y fotos en el álbum del usuario.
"""

from __future__ import annotations

import os

import httpx
from langchain_core.tools import tool

from database import save_album_entry

DIARY_SERVICE_URL = os.getenv("DIARY_SERVICE_URL", "http://localhost:8083")


@tool
def save_to_album(
    user_id: int,
    session_id: str,
    content: str,
    entry_type: str = "texto",
    image_url: str = "",
) -> str:
    """Guarda un mensaje, reflexión o foto en el álbum personal del usuario.
    Usa esta herramienta cuando el usuario quiera guardar un momento especial,
    una reflexión positiva, un logro personal, o una foto en su álbum.

    Args:
        user_id: ID del usuario.
        session_id: ID de la sesión actual.
        content: Texto del mensaje, reflexión o descripción de la foto a guardar.
        entry_type: Tipo de entrada: 'texto', 'foto', 'momento', 'reflexion'.
        image_url: URL de la imagen si es una foto (opcional).
    """
    try:
        # 1. Guardar en la base de datos local del agente
        entry_id = save_album_entry(
            user_id=user_id,
            session_id=session_id,
            content=content,
            image_url=image_url if image_url else None,
            entry_type=entry_type,
        )

        # 2. Intentar sincronizar con el servicio de diario/álbum
        synced = False
        try:
            payload = {
                "contenido": content,
                "tipo": entry_type,
            }
            if image_url:
                payload["imagenUrl"] = image_url

            response = httpx.post(
                f"{DIARY_SERVICE_URL}/api/album",
                json=payload,
                timeout=10.0,
            )
            if response.status_code < 400:
                synced = True
        except Exception:
            # Si el servicio de diario no está disponible, no falla
            pass

        sync_msg = " y sincronizado con tu álbum" if synced else ""
        return (
            f"✅ Guardado exitosamente en tu álbum{sync_msg}.\n"
            f"   Tipo: {entry_type}\n"
            f"   Contenido: {content[:100]}{'...' if len(content) > 100 else ''}"
        )

    except Exception as e:
        return f"Error al guardar en el álbum: {str(e)}"
