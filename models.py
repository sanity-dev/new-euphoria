"""
Sanity Agent – Pydantic Models
Modelos de datos para la API, base de datos y comunicación entre herramientas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════
# Request / Response del Chat
# ═══════════════════════════════════════════════════════════

class MensajeRequest(BaseModel):
    """Mensaje entrante del usuario."""
    mensaje: str
    session_id: Optional[str] = None
    user_id: Optional[int] = None


class MensajeResponse(BaseModel):
    """Respuesta del agente al usuario."""
    respuesta: str
    emociones_detectadas: list[str] = Field(default_factory=list)
    timestamp: str
    session_id: str
    acciones_realizadas: list[str] = Field(default_factory=list)


class HistorialItem(BaseModel):
    """Un mensaje individual del historial."""
    rol: str
    mensaje: str
    timestamp: str


class HistorialResponse(BaseModel):
    """Respuesta con el historial completo de una sesión."""
    historial: list[HistorialItem] = Field(default_factory=list)
    session_id: str
    total_mensajes: int = 0


class StatusResponse(BaseModel):
    """Respuesta genérica de estado."""
    status: str
    mensaje: Optional[str] = None
    timestamp: str


# ═══════════════════════════════════════════════════════════
# Recordatorios de Hábitos
# ═══════════════════════════════════════════════════════════

class ReminderCreate(BaseModel):
    """Datos para crear un nuevo recordatorio."""
    user_id: int
    session_id: str
    habit_name: str
    description: Optional[str] = None
    frequency: str = "diario"
    reminder_time: Optional[str] = None


class Reminder(BaseModel):
    """Un recordatorio existente."""
    id: int
    user_id: int
    habit_name: str
    description: Optional[str] = None
    frequency: str
    reminder_time: Optional[str] = None
    is_active: bool = True
    created_at: str


# ═══════════════════════════════════════════════════════════
# Entradas del Álbum
# ═══════════════════════════════════════════════════════════

class AlbumEntryCreate(BaseModel):
    """Datos para guardar una entrada en el álbum."""
    user_id: int
    session_id: str
    content: Optional[str] = None
    image_url: Optional[str] = None
    entry_type: str = "texto"


class AlbumEntry(BaseModel):
    """Una entrada de álbum existente."""
    id: int
    user_id: int
    content: Optional[str] = None
    image_url: Optional[str] = None
    entry_type: str
    created_at: str


# ═══════════════════════════════════════════════════════════
# Datos de otros servicios
# ═══════════════════════════════════════════════════════════

class UserProfile(BaseModel):
    """Perfil del usuario obtenido del servicio de usuarios."""
    id_persona: int
    nombre: str
    correo: str
    telefono: Optional[str] = None
    tipo_usuario: str = "USUARIO"
    contacto_emergencia: Optional[str] = None
    telefono_contacto_emergencia: Optional[str] = None
    mensaje_emergencia: Optional[str] = None
    telefono_apoyo_alternativo: Optional[str] = None


class AppointmentInfo(BaseModel):
    """Información de una cita del servicio de especialistas."""
    id: Optional[int] = None
    paciente_id: int
    specialist_user_id: int
    tipo_sesion: str
    fecha: str
    nombre_terapeuta: Optional[str] = None


class SpecialistInfo(BaseModel):
    """Información de un especialista."""
    id: Optional[int] = None
    user_id: int
    nombre: Optional[str] = None
    titulo_profesional: str
    presentacion: str
    especialidades: list[str] = Field(default_factory=list)
    servicios: list[str] = Field(default_factory=list)
    disponibilidad: Optional[str] = None
