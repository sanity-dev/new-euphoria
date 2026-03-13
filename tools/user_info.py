"""
Sanity Agent – Tool: User Info
Obtiene información del perfil del usuario desde el microservicio de usuarios.
"""

from __future__ import annotations

import os

import httpx
from langchain_core.tools import tool

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL", "http://localhost:8081")


@tool
def get_user_profile(user_id: int) -> str:
    """Obtiene el perfil completo del usuario, incluyendo nombre, correo,
    contacto de emergencia y teléfono de emergencia.
    Usa esta herramienta cuando necesites información personal del usuario
    o cuando el usuario pregunte sobre su contacto de emergencia."""
    try:
        response = httpx.get(
            f"{USERS_SERVICE_URL}/api/personas/{user_id}",
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

        info_parts = [
            f"Nombre: {data.get('nombre', 'No disponible')}",
            f"Correo: {data.get('correo', 'No disponible')}",
            f"Teléfono: {data.get('telefono', 'No registrado')}",
        ]

        if data.get("contactoEmergencia"):
            info_parts.append(f"Contacto de emergencia: {data['contactoEmergencia']}")
        if data.get("telefonoContactoEmergencia"):
            info_parts.append(f"Teléfono contacto emergencia: {data['telefonoContactoEmergencia']}")
        if data.get("mensajeEmergencia"):
            info_parts.append(f"Mensaje de emergencia configurado: {data['mensajeEmergencia']}")
        if data.get("telefonoApoyoAlternativo"):
            info_parts.append(f"Teléfono apoyo alternativo: {data['telefonoApoyoAlternativo']}")

        return "\n".join(info_parts)

    except httpx.HTTPStatusError as e:
        return f"Error al obtener el perfil del usuario: HTTP {e.response.status_code}"
    except Exception as e:
        return f"Error de conexión con el servicio de usuarios: {str(e)}"
