"""
Sanity Agent – Tool: Chat Memory
Persistencia de conversaciones en Azure SQL.
"""

from __future__ import annotations

from langchain_core.tools import tool

from database import (
    get_or_create_conversation,
    save_message,
    get_messages,
    deactivate_conversation,
)


@tool
def get_conversation_history(session_id: str) -> str:
    """Obtiene el historial de conversación reciente del usuario.
    Usa esta herramienta cuando necesites contexto de lo que el usuario
    ha dicho anteriormente en la conversación."""
    messages = get_messages(session_id, limit=20)
    if not messages:
        return "No hay historial de conversación previo."

    lines = []
    for msg in messages:
        role_label = "Usuario" if msg["rol"] == "usuario" else "Tú (Asistente)"
        lines.append(f"{role_label}: {msg['mensaje']}")
    return "\n".join(lines)
