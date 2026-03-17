"""
Sanity Agent – Tool: User Info
Obtiene información del perfil del usuario desde el microservicio de usuarios.
Requiere token de autenticación para acceder a los datos.
"""

from __future__ import annotations

import os
from datetime import datetime

import httpx
from langchain_core.tools import tool

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL", "http://localhost:8081")


@tool
def get_user_profile(user_id: int, auth_token: str = "") -> str:
    """
    Obtiene el perfil completo del usuario desde el microservicio de usuarios.
    
    INFORMACIÓN QUE PUEDES OBTENER:
    - Nombre del usuario
    - Correo electrónico
    - Teléfono
    - Contacto de emergencia (nombre)
    - Teléfono de contacto de emergencia
    - Mensaje de emergencia personalizado
    - Teléfono de apoyo alternativo
    
    CUÁNDO USAR ESTA HERRAMIENTA:
    - Cuando el usuario pregunte directamente por su información personal
    - Cuando el usuario pregunte "cuál es mi nombre", "mi correo", etc.
    - Cuando el usuario necesite saber su contacto de emergencia
    - Cuando quieras personalizar tu respuesta con el nombre del usuario
    
    ARGS:
        user_id: ID numérico del usuario. Si es None o 0, retorna error.
        auth_token: Token JWT de autenticación (requerido).
    
    RETURNS:
        String con la información del usuario formateada, o mensaje de error.
    
    EJEMPLOS DE USO:
    - Usuario: "¿Cuál es mi nombre?" → Usa esta herramienta con su user_id y token
    - Usuario: "¿Qué correo tengo registrado?" → Usa esta herramienta
    - Usuario: "¿Quién es mi contacto de emergencia?" → Usa esta herramienta
    """
    if not user_id or user_id <= 0:
        return "⚠️ No se pudo identificar al usuario. Por favor, verifica que hayas iniciado sesión correctamente."
    
    if not auth_token:
        return "⚠️ No se proporcionó token de autenticación. Por favor, inicia sesión nuevamente."
    
    try:
        print(f"[TOOL: get_user_profile] Consultando user_id={user_id}")
        
        # Preparar headers con autenticación
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
        
        response = httpx.get(
            f"{USERS_SERVICE_URL}/api/personas/{user_id}",
            headers=headers,
            timeout=10.0,
        )
        
        print(f"[TOOL: get_user_profile] Response status: {response.status_code}")
        
        if response.status_code == 404:
            return f"⚠️ No se encontró un usuario con ID {user_id}."
        
        if response.status_code == 401:
            return "⚠️ Token de autenticación inválido o expirado. Por favor, inicia sesión nuevamente."
        
        if response.status_code == 403:
            return "⚠️ No tienes permisos para acceder a esta información."
        
        response.raise_for_status()
        data = response.json()

        # Construir respuesta con la información disponible
        info_parts = []
        
        nombre = data.get('nombre')
        if nombre:
            info_parts.append(f"✓ Nombre: {nombre}")
        else:
            info_parts.append("○ Nombre: No disponible")
        
        correo = data.get('correo')
        if correo:
            info_parts.append(f"✓ Correo: {correo}")
        else:
            info_parts.append("○ Correo: No disponible")
        
        telefono = data.get('telefono')
        if telefono:
            info_parts.append(f"✓ Teléfono: {telefono}")
        
        # Información de emergencia
        contacto_emergencia = data.get('contactoEmergencia')
        telefono_emergencia = data.get('telefonoContactoEmergencia')
        mensaje_emergencia = data.get('mensajeEmergencia')
        telefono_apoyo = data.get('telefonoApoyoAlternativo')
        
        if contacto_emergencia or telefono_emergencia:
            info_parts.append("")  # Línea en blanco
            info_parts.append("🆘 CONTACTOS DE EMERGENCIA:")
            
            if contacto_emergencia:
                info_parts.append(f"   • Nombre: {contacto_emergencia}")
            if telefono_emergencia:
                info_parts.append(f"   • Teléfono: {telefono_emergencia}")
            if mensaje_emergencia:
                info_parts.append(f"   • Mensaje: {mensaje_emergencia}")
            if telefono_apoyo:
                info_parts.append(f"   • Apoyo alternativo: {telefono_apoyo}")

        return "\n".join(info_parts)

    except httpx.TimeoutException:
        print(f"[TOOL: get_user_profile] Timeout conectando a {USERS_SERVICE_URL}")
        return "⏱️ El servicio de usuarios no responde. Por favor, intenta de nuevo en unos segundos."
    except httpx.HTTPStatusError as e:
        print(f"[TOOL: get_user_profile] HTTP Error: {e.response.status_code}")
        return f"❌ Error al obtener el perfil del usuario: HTTP {e.response.status_code}"
    except Exception as e:
        print(f"[TOOL: get_user_profile] Error: {str(e)}")
        return f"❌ Error de conexión con el servicio de usuarios: {str(e)}"
