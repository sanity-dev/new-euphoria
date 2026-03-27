"""
Sanity Agent – Tool: Appointments
Gestión de citas con terapeutas a través del microservicio de especialistas.
Requiere token de autenticación para acceder a los datos.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import httpx
from langchain_core.tools import tool

SPECIALIST_SERVICE_URL = os.getenv("SPECIALIST_SERVICE_URL", "http://localhost:8082")


@tool
def get_upcoming_appointments(user_id: int, auth_token: str) -> str:
    """Obtiene las próximas citas programadas del usuario con sus terapeutas.
    Usa esta herramienta cuando el usuario pregunte por sus citas,
    cuándo tiene su próxima sesión, o qué terapeutas lo atienden.
    
    Args:
        user_id: ID del usuario.
        auth_token: Token JWT de autenticación.
    """
    if not auth_token:
        return "⚠️ No se proporcionó token de autenticación."
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = httpx.get(
            f"{SPECIALIST_SERVICE_URL}/api/appointment/user/{user_id}",
            headers=headers,
            timeout=10.0,
        )
        response.raise_for_status()
        appointments = response.json()

        if not appointments:
            return "No tienes citas programadas actualmente."

        # Filtrar citas futuras
        now = datetime.now()
        upcoming = []
        for apt in appointments:
            fecha_str = apt.get("fecha", "")
            try:
                fecha = datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
                if fecha > now:
                    upcoming.append(apt)
            except (ValueError, TypeError):
                upcoming.append(apt)

        if not upcoming:
            return "No tienes citas futuras programadas. ¿Te gustaría agendar una?"

        # Ordenar por fecha
        upcoming.sort(key=lambda a: a.get("fecha", ""))

        lines = [f"Tienes {len(upcoming)} cita(s) próxima(s):"]
        for i, apt in enumerate(upcoming, 1):
            parts = [
                f"\n{i}. Fecha: {apt.get('fecha', 'No especificada')}",
                f"   Tipo de sesión: {apt.get('tipoSesion', 'Consulta general')}",
            ]
            if apt.get("specialistUserId"):
                parts.append(f"   ID del terapeuta: {apt['specialistUserId']}")
            lines.extend(parts)

        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return "⚠️ Token inválido o expirado. Por favor, inicia sesión nuevamente."
        return f"Error al consultar citas: HTTP {e.response.status_code}"
    except Exception as e:
        return f"Error de conexión con el servicio de citas: {str(e)}"


@tool
def get_available_therapists(auth_token: str) -> str:
    """Obtiene la lista de terapeutas disponibles con sus especialidades y horarios.
    Usa esta herramienta cuando el usuario quiera buscar un terapeuta,
    conocer las opciones disponibles, o antes de agendar una cita.
    
    Args:
        auth_token: Token JWT de autenticación.
    """
    if not auth_token:
        return "⚠️ No se proporcionó token de autenticación."
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = httpx.get(
            f"{SPECIALIST_SERVICE_URL}/api/specialist",
            headers=headers,
            timeout=20.0,
        )
        response.raise_for_status()
        specialists = response.json()

        if not specialists:
            return "No hay terapeutas disponibles en este momento."

        lines = [f"Hay {len(specialists)} terapeuta(s) disponible(s):"]
        for i, sp in enumerate(specialists, 1):
            especialidades = sp.get("especialidades", [])
            if isinstance(especialidades, str):
                try:
                    especialidades = json.loads(especialidades)
                except json.JSONDecodeError:
                    especialidades = [especialidades]

            servicios = sp.get("servicios", [])
            if isinstance(servicios, str):
                try:
                    servicios = json.loads(servicios)
                except json.JSONDecodeError:
                    servicios = [servicios]

            parts = [
                f"\n{i}. {sp.get('nombre', 'Terapeuta')}",
                f"   Título: {sp.get('tituloProfesional', 'No especificado')}",
                f"   Especialidades: {', '.join(especialidades) if especialidades else 'General'}",
                f"   Servicios: {', '.join(servicios) if servicios else 'Consulta'}",
                f"   Presentación: {sp.get('presentacion', '')[:150]}...",
            ]

            if sp.get("disponibilidad"):
                parts.append(f"   Disponibilidad: {sp['disponibilidad']}")

            parts.append(f"   ID para reservar: {sp.get('userId', sp.get('id', 'N/A'))}")
            lines.extend(parts)

        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return "⚠️ Tu sesión ha expirado. Por favor, cierra sesión, vuelve a iniciarla y escríbeme de nuevo."
        if e.response.status_code == 403:
            return "⚠️ No tienes permisos para consultar esta información."
        return f"Error al consultar terapeutas: HTTP {e.response.status_code}"
    except httpx.TimeoutException:
        return "⚠️ El servicio de terapeutas tardó demasiado en responder. Es posible que tu sesión haya expirado. Por favor, cierra sesión y vuelve a iniciarla."
    except Exception as e:
        return f"Error de conexión con el servicio de especialistas: {str(e)}"


@tool
def book_appointment(
    user_id: int,
    specialist_user_id: int,
    session_type: str,
    date_time: str,
    auth_token: str,
) -> str:
    """Reserva una cita con un terapeuta específico.
    Usa esta herramienta cuando el usuario confirme que quiere agendar una cita.
    El user_id (paciente) y auth_token se inyectan automáticamente.
    Solo necesitas proporcionar: specialist_user_id, session_type y date_time.

    IMPORTANTE: Usa el specialist_user_id que obtuviste de get_available_therapists.
    Si solo hay un terapeuta disponible, usa su ID directamente sin preguntar.
    Si el usuario no especifica tipo de sesión, usa 'Consulta individual' por defecto.

    Args:
        user_id: ID del usuario/paciente que reserva (se inyecta automáticamente).
        specialist_user_id: ID del terapeuta con quien reservar (obtenido de get_available_therapists).
        session_type: Tipo de sesión (ej: 'Consulta individual', 'Seguimiento').
        date_time: Fecha y hora en formato ISO 8601 (ej: '2026-03-20T10:00:00').
        auth_token: Token JWT de autenticación (se inyecta automáticamente).
    """
    if not auth_token:
        return "⚠️ No se proporcionó token de autenticación."
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        payload = {
            "pacienteID": user_id,
            "specialistUserId": specialist_user_id,
            "tipoSesion": session_type,
            "fecha": date_time,
        }

        response = httpx.post(
            f"{SPECIALIST_SERVICE_URL}/api/appointment",
            json=payload,
            headers=headers,
            timeout=10.0,
        )
        response.raise_for_status()
        result = response.json()

        return (
            f"✅ Cita reservada exitosamente.\n"
            f"   ID de cita: {result.get('id', 'N/A')}\n"
            f"   Fecha: {date_time}\n"
            f"   Tipo: {session_type}\n"
            f"   Terapeuta ID: {specialist_user_id}"
        )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return "⚠️ Token inválido o expirado. Por favor, inicia sesión nuevamente."
        error_detail = ""
        try:
            error_detail = e.response.json().get("message", e.response.text)
        except Exception:
            error_detail = e.response.text
        return f"Error al reservar la cita: {error_detail}"
    except Exception as e:
        return f"Error de conexión con el servicio de citas: {str(e)}"
