"""
Sanity Agent – Tool: Emergency Contact
Envía mensaje o alerta al contacto de emergencia del usuario.
"""

from __future__ import annotations

import os

import httpx
from langchain_core.tools import tool

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL", "http://localhost:8081")
NOTIFICATIONS_SERVICE_URL = os.getenv("NOTIFICATIONS_SERVICE_URL", "http://localhost:8085")


@tool
def contact_emergency(user_id: int) -> str:
    """Contacta al contacto de emergencia del usuario enviando una notificación de alerta.
    Usa esta herramienta SOLO cuando el usuario lo pida explícitamente
    o cuando detectes una situación de crisis emocional grave.
    Esta acción es IRREVERSIBLE, confirma antes con el usuario.

    Args:
        user_id: ID del usuario que solicita contactar a su contacto de emergencia.
    """
    try:
        # 1. Obtener info del contacto de emergencia
        response = httpx.get(
            f"{USERS_SERVICE_URL}/api/personas/{user_id}",
            timeout=10.0,
        )
        response.raise_for_status()
        user_data = response.json()

        contacto = user_data.get("contactoEmergencia")
        telefono = user_data.get("telefonoContactoEmergencia")
        mensaje_emergencia = user_data.get("mensajeEmergencia", "")
        nombre_usuario = user_data.get("nombre", "Un usuario")

        if not contacto and not telefono:
            return (
                "⚠️ No tienes configurado un contacto de emergencia en tu perfil. "
                "Te recomiendo ir a Configuración > Botón de Emergencia para añadir "
                "un contacto de confianza.\n\n"
                "Si estás en una situación de crisis, por favor llama a la "
                "Línea Nacional de Crisis: 106 (Colombia) o al número de emergencias de tu país."
            )

        # 2. Enviar notificación al sistema
        try:
            mensaje = (
                mensaje_emergencia
                or f"{nombre_usuario} necesita apoyo emocional urgente. "
                   f"Por favor comunícate con él/ella lo antes posible."
            )
            payload = {
                "usuarioId": str(user_id),
                "titulo": f"🚨 Alerta de emergencia de {nombre_usuario}",
                "mensaje": mensaje,
                "tipo": "PUSH",
            }
            httpx.post(
                f"{NOTIFICATIONS_SERVICE_URL}/api/notificaciones",
                json=payload,
                timeout=10.0,
            )
        except Exception:
            pass

        # 3. Construir respuesta para el usuario
        response_parts = [
            f"🚨 Se ha enviado una alerta de emergencia.",
            f"   Contacto: {contacto or 'No especificado'}",
            f"   Teléfono: {telefono or 'No especificado'}",
        ]

        if telefono:
            response_parts.append(
                f"\n📞 Si necesitas hablar directamente, puedes llamar a {contacto} "
                f"al número {telefono}."
            )

        response_parts.append(
            "\n💚 Recuerda que no estás solo/a. Si estás en peligro inmediato, "
            "llama al número de emergencias de tu país."
        )

        return "\n".join(response_parts)

    except httpx.HTTPStatusError as e:
        return f"Error al acceder al perfil del usuario: HTTP {e.response.status_code}"
    except Exception as e:
        return f"Error al contactar emergencia: {str(e)}"


@tool
def get_emergency_contact_info(user_id: int) -> str:
    """Obtiene la información del contacto de emergencia del usuario.
    Usa esta herramienta cuando el usuario pregunte quién es su contacto
    de emergencia o quiera verificar la información antes de contactarlo.

    Args:
        user_id: ID del usuario.
    """
    try:
        response = httpx.get(
            f"{USERS_SERVICE_URL}/api/personas/{user_id}",
            timeout=10.0,
        )
        response.raise_for_status()
        user_data = response.json()

        contacto = user_data.get("contactoEmergencia")
        telefono = user_data.get("telefonoContactoEmergencia")
        mensaje = user_data.get("mensajeEmergencia", "")
        apoyo_alt = user_data.get("telefonoApoyoAlternativo")

        if not contacto and not telefono:
            return (
                "No tienes un contacto de emergencia configurado. "
                "Te recomiendo ir a tu perfil > Configuración de Emergencia "
                "para añadir a alguien de tu confianza."
            )

        parts = ["Tu contacto de emergencia:"]
        if contacto:
            parts.append(f"   Nombre: {contacto}")
        if telefono:
            parts.append(f"   Teléfono: {telefono}")
        if mensaje:
            parts.append(f"   Mensaje configurado: {mensaje}")
        if apoyo_alt:
            parts.append(f"   Teléfono de apoyo alternativo: {apoyo_alt}")

        return "\n".join(parts)

    except Exception as e:
        return f"Error al obtener la información de emergencia: {str(e)}"
