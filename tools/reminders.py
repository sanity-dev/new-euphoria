"""
Sanity Agent – Tool: Reminders
Gestión de recordatorios de hábitos saludables.
Requiere token de autenticación para acceder a los datos.
"""

from __future__ import annotations

import os

import httpx
from langchain_core.tools import tool

from database import create_reminder, get_reminders, deactivate_reminder

NOTIFICATIONS_SERVICE_URL = os.getenv("NOTIFICATIONS_SERVICE_URL", "http://localhost:8085")


@tool
def create_healthy_habit_reminder(
    user_id: int,
    session_id: str,
    habit_name: str,
    description: str = "",
    frequency: str = "diario",
    reminder_time: str = "",
    auth_token: str = "",
) -> str:
    """Crea un recordatorio de hábito saludable para el usuario.
    Usa esta herramienta cuando el usuario quiera establecer un recordatorio
    para meditación, ejercicio, hidratación, sueño, respiración, journaling,
    o cualquier otro hábito saludable. También puedes sugerirlo proactivamente
    si detectas que el usuario podría beneficiarse de un hábito específico.

    Args:
        user_id: ID del usuario.
        session_id: ID de la sesión actual.
        habit_name: Nombre del hábito (ej: 'Meditación matutina', 'Hidratación').
        description: Descripción detallada del hábito.
        frequency: Frecuencia: 'diario', 'semanal', 'cada 2 horas', etc.
        reminder_time: Hora del recordatorio en formato HH:MM (ej: '08:00').
        auth_token: Token JWT de autenticación.
    """
    try:
        # 1. Guardar en base de datos del agente
        rem_id = create_reminder(
            user_id=user_id,
            session_id=session_id,
            habit_name=habit_name,
            description=description if description else None,
            frequency=frequency,
            reminder_time=reminder_time if reminder_time else None,
        )

        # 2. Crear notificación en el servicio de notificaciones (con auth)
        try:
            headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
            
            payload = {
                "usuarioId": str(user_id),
                "titulo": f"Recordatorio: {habit_name}",
                "mensaje": description or f"Es momento de practicar: {habit_name}",
                "tipo": "SISTEMA",
            }
            httpx.post(
                f"{NOTIFICATIONS_SERVICE_URL}/api/notifications",
                json=payload,
                headers=headers,
                timeout=10.0,
            )
        except Exception:
            pass  # Si el servicio de notificaciones no está disponible, no falla

        return (
            f"✅ Recordatorio creado exitosamente.\n"
            f"   Hábito: {habit_name}\n"
            f"   Frecuencia: {frequency}\n"
            f"   Hora: {reminder_time or 'No especificada'}\n"
            f"   Descripción: {description or 'Sin descripción'}"
        )

    except Exception as e:
        return f"Error al crear el recordatorio: {str(e)}"


@tool
def list_reminders(user_id: int, auth_token: str = "") -> str:
    """Lista todos los recordatorios activos del usuario.
    Usa esta herramienta cuando el usuario pregunte por sus recordatorios,
    hábitos establecidos, o quiera ver qué rutinas tiene configuradas.
    
    Args:
        user_id: ID del usuario.
        auth_token: Token JWT de autenticación.
    """
    try:
        reminders = get_reminders(user_id, only_active=True)

        if not reminders:
            return "No tienes recordatorios activos actualmente. ¿Te gustaría crear uno?"

        lines = [f"Tienes {len(reminders)} recordatorio(s) activo(s):"]
        for i, rem in enumerate(reminders, 1):
            parts = [
                f"\n{i}. {rem['habit_name']}",
                f"   Frecuencia: {rem['frequency']}",
            ]
            if rem.get("reminder_time"):
                parts.append(f"   Hora: {rem['reminder_time']}")
            if rem.get("description"):
                parts.append(f"   Descripción: {rem['description']}")
            parts.append(f"   ID: {rem['id']}")
            lines.extend(parts)

        return "\n".join(lines)

    except Exception as e:
        return f"Error al listar recordatorios: {str(e)}"


@tool
def delete_reminder(reminder_id: int, auth_token: str = "") -> str:
    """Desactiva un recordatorio existente.
    Usa esta herramienta cuando el usuario quiera eliminar o desactivar
    un recordatorio específico. Necesitas el ID del recordatorio.

    Args:
        reminder_id: ID del recordatorio a desactivar.
        auth_token: Token JWT de autenticación.
    """
    try:
        success = deactivate_reminder(reminder_id)
        if success:
            return f"✅ Recordatorio #{reminder_id} desactivado correctamente."
        else:
            return f"No se encontró el recordatorio con ID {reminder_id}."
    except Exception as e:
        return f"Error al desactivar el recordatorio: {str(e)}"
