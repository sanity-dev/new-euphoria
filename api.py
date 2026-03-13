"""
Sanity Agent – FastAPI Application
Endpoints compatibles con el frontend Angular (EuphoriaService).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
    create_reminder,
    get_reminders,
    deactivate_reminder,
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
async def chat(request: MensajeRequest):
    """
    Envía un mensaje al agente terapeuta y recibe una respuesta.
    Compatible con EuphoriaService.enviarMensaje().
    """
    if not request.mensaje or not request.mensaje.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    session_id = request.session_id or f"anonymous_{datetime.now().timestamp()}"

    try:
        result = await process_message(
            session_id=session_id,
            message=request.mensaje.strip(),
            user_id=request.user_id,
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


@app.get("/historial/{session_id}", response_model=HistorialResponse)
async def get_history(session_id: str):
    """
    Obtiene el historial de conversación de una sesión.
    Compatible con EuphoriaService.obtenerHistorial().
    """
    try:
        messages = get_messages(session_id, limit=100)
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
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo historial: {str(e)}",
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
