"""
Sanity Agent – FastAPI Application
Endpoints compatibles con el frontend Angular (EuphoriaService).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Header

from models import (
    MensajeRequest,
    MensajeResponse,
    HistorialResponse,
    HistorialItem,
    StatusResponse,
    ReminderCreate,
    Reminder,
)
from agent import process_message
from database import (
    get_messages,
    deactivate_conversation,
    get_user_conversations,
    create_reminder,
    get_reminders,
    deactivate_reminder,
    migrate_conversations_with_user_id,
)


# ═══════════════════════════════════════════════════════════
# App FastAPI
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="Sanity Agent – EuphorIA",
    description="Terapeuta virtual profesional con IA para la aplicación Sanity",
    version="1.0.0",
)




# ═══════════════════════════════════════════════════════════
# Endpoints principales del Chat (compatibles con EuphoriaService)
# ═══════════════════════════════════════════════════════════

@app.post("/chat", response_model=MensajeResponse)
async def chat(
    request: MensajeRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """
    Envía un mensaje al agente terapeuta y recibe una respuesta.
    Compatible con EuphoriaService.enviarMensaje().
    """
    if not request.mensaje or not request.mensaje.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    session_id = request.session_id or f"anonymous_{datetime.now().timestamp()}"

    # Si no viene user_id en el request, intentar extraerlo del session_id
    user_id = request.user_id
    if not user_id and session_id:
        user_id = _extract_user_id_from_session(session_id)
        if user_id:
            print(f"[DEBUG] Extraído user_id={user_id} del session_id={session_id}")
    
    # Extraer token de autenticación (quitar "Bearer " si existe)
    auth_token = None
    if authorization:
        auth_token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization

    try:
        result = await process_message(
            session_id=session_id,
            message=request.mensaje.strip(),
            user_id=user_id,
            auth_token=auth_token,
        )

        return MensajeResponse(
            respuesta=result["respuesta"],
            emociones_detectadas=result.get("emociones_detectadas", []),
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            acciones_realizadas=result.get("acciones_realizadas", []),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando el mensaje: {str(e)}",
        )


# ═══════════════════════════════════════════════════════════
# Utilidades para autenticación
# ═══════════════════════════════════════════════════════════

def get_auth_token(authorization: Optional[str]) -> Optional[str]:
    """Extrae el token del header Authorization."""
    if not authorization:
        return None
    return authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization


def _extract_user_id_from_session(session_id: str) -> int | None:
    """
    Intenta extraer el user_id del session_id.
    Formatos soportados:
    - mood_check_{user_id}_{timestamp}
    - session_guest_{user_id}_{timestamp}_{random}
    """
    import re

    # Pattern: mood_check_7_1773684554154
    match = re.match(r'^mood_check_(\d+)_\d+$', session_id)
    if match:
        return int(match.group(1))

    # Pattern: session_guest_1773684440805_4oliyc (el user_id podría ser el primer número)
    match = re.match(r'^session_guest_(\d+)_\w+$', session_id)
    if match:
        # En este caso, el primer número parece ser un timestamp, no el user_id
        # No extraemos user_id aquí
        pass

    return None


@app.get("/historial/{session_id}", response_model=HistorialResponse)
async def get_history(session_id: str):
    """
    Obtiene el historial de conversación de una sesión.
    Compatible con EuphoriaService.obtenerHistorial().
    """
    try:
        print(f"[DEBUG] Getting history for session_id={session_id}")
        # Se incluye el historial de conversaciones inactivas para poder ver
        # los chats anteriores desde el sidebar
        messages = get_messages(session_id, limit=100, include_inactive=True)
        print(f"[DEBUG] Retrieved {len(messages)} messages for session_id={session_id}")
        historial = [
            HistorialItem(
                rol=msg["rol"],
                mensaje=msg["mensaje"],
                timestamp=msg["timestamp"],
            )
            for msg in messages
        ]
        return HistorialResponse(
            historial=historial,
            session_id=session_id,
            total_mensajes=len(historial),
        )
    except Exception as e:
        print(f"[ERROR] Error getting history for session_id={session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo historial: {str(e)}",
        )


@app.post("/mood-check")
async def mood_check(
    request: MensajeRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """
    Endpoint especializado para check de estado de ánimo desde el dashboard.
    Usa la herramienta check_mood_dashboard del agente para generar una respuesta
    terapéutica breve que NO se guarda en el historial de conversaciones principal.
    Compatible con el selector de estado de ánimo del dashboard.
    """
    if not request.mensaje or not request.mensaje.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    # Extraer el mood del mensaje (formato esperado: "El usuario se siente {mood}")
    mensaje = request.mensaje.strip()
    session_id = request.session_id or f"mood_{datetime.now().timestamp()}"
    user_id = request.user_id
    auth_token = get_auth_token(authorization)

    # Si no viene user_id, intentar extraerlo del session_id
    if not user_id and session_id:
        user_id = _extract_user_id_from_session(session_id)

    try:
        # Importar la herramienta directamente
        from tools.mood_check import check_mood_dashboard

        # Extraer el estado de ánimo del mensaje
        mood = _extract_mood_from_message(mensaje)

        # Ejecutar la herramienta
        respuesta = check_mood_dashboard.invoke({"mood": mood, "user_id": user_id})

        return MensajeResponse(
            respuesta=respuesta,
            emociones_detectadas=[mood],
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            acciones_realizadas=["check_mood_dashboard: OK"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en mood check: {str(e)}",
        )


def _extract_mood_from_message(message: str) -> str:
    """
    Extrae el estado de ánimo del mensaje.
    Formatos soportados:
    - "El usuario se siente {mood}"
    - "El usuario acaba de indicar que se siente {mood}"
    - "{mood}" (si es solo la palabra del mood)
    """
    import re
    
    message_lower = message.lower()
    
    # Patrones posibles
    patterns = [
        r'se siente\s+(\w+)',
        r'se sienta\s+(\w+)',
        r'está\s+(\w+)',
        r'esta\s+(\w+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message_lower)
        if match:
            return match.group(1)
    
    # Si no hay match, devolver la primera palabra que parezca un mood
    moods_validos = ["triste", "ansioso", "feliz", "calma", "neutral", "enojado", "miedo", "frustrado", "enojada", "frustrada"]
    for mood in moods_validos:
        if mood in message_lower:
            return mood
    
    # Default
    return "neutral"


@app.get("/conversaciones/{user_id}")
async def get_conversations(user_id: int):
    """Obtiene la lista de todas las sesiones de chat de un usuario."""
    try:
        conversations = get_user_conversations(user_id)
        return {"conversations": conversations, "total": len(conversations)}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo conversaciones: {str(e)}",
        )


@app.post("/migrate-conversations")
async def migrate_conversations():
    """
    Migra las conversaciones antiguas asignando user_id basado en el session_id.
    Endpoint temporal para corregir datos existentes.
    """
    try:
        migrated_count = migrate_conversations_with_user_id()
        return {
            "status": "success",
            "migrated_count": migrated_count,
            "message": f"{migrated_count} conversaciones migradas",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error migrando conversaciones: {str(e)}",
        )


@app.delete("/sesion/{session_id}", response_model=StatusResponse)
async def clear_session(session_id: str):
    """
    Limpia / desactiva una sesión de conversación.
    Compatible con EuphoriaService.limpiarMemoria().
    """
    try:
        success = deactivate_conversation(session_id)
        return StatusResponse(
            status="ok" if success else "no_sessions_found",
            mensaje="Sesión limpiada correctamente." if success else "No se encontraron sesiones activas.",
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error limpiando sesión: {str(e)}",
        )


@app.get("/health")
async def health_check():
    """
    Health check del agente.
    Compatible con EuphoriaService.verificarConexion().
    """
    return {
        "status": "ok",
        "service": "sanity-agent",
        "timestamp": datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════════════
# Endpoints de Recordatorios
# ═══════════════════════════════════════════════════════════

@app.get("/reminders/{user_id}")
async def get_user_reminders(user_id: int):
    """Obtiene los recordatorios activos de un usuario."""
    try:
        reminders = get_reminders(user_id, only_active=True)
        return {"reminders": reminders, "total": len(reminders)}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo recordatorios: {str(e)}",
        )


@app.post("/reminders")
async def create_user_reminder(request: ReminderCreate):
    """Crea un nuevo recordatorio de hábito saludable."""
    try:
        rem_id = create_reminder(
            user_id=request.user_id,
            session_id=request.session_id,
            habit_name=request.habit_name,
            description=request.description,
            frequency=request.frequency,
            reminder_time=request.reminder_time,
        )
        return {"id": rem_id, "status": "created"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creando recordatorio: {str(e)}",
        )


@app.delete("/reminders/{reminder_id}")
async def remove_reminder(reminder_id: int):
    """Desactiva un recordatorio."""
    try:
        success = deactivate_reminder(reminder_id)
        if not success:
            raise HTTPException(status_code=404, detail="Recordatorio no encontrado.")
        return {"status": "deleted", "id": reminder_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error eliminando recordatorio: {str(e)}",
        )
