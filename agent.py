"""
Sanity Agent – LangChain Agent Core
Agente terapeuta profesional con LangChain + Gemini.
"""

from __future__ import annotations

import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# ── Importar todas las herramientas ──────────────────────────────────
from tools.user_info import get_user_profile
from tools.appointments import (
    get_upcoming_appointments,
    get_available_therapists,
    book_appointment,
)
from tools.album import save_to_album, list_album_entries, delete_from_album
from tools.reminders import (
    create_healthy_habit_reminder,
    list_reminders,
    delete_reminder,
)
from tools.emergency import contact_emergency, get_emergency_contact_info
from tools.chat_memory import get_conversation_history
from tools.mood_check import check_mood_dashboard, get_mood_coping_strategy
from tools.call_emergency_contact import call_emergency_contact

from database import (
    get_or_create_conversation,
    save_message,
    get_messages,
)


# ═══════════════════════════════════════════════════════════
# System Prompt – Rol del Terapeuta
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Eres EuphorIA, un terapeuta virtual profesional de la aplicación Sanity. \
Tu rol es EXCLUSIVAMENTE ser un acompañante terapéutico empático y profesional, \
especializado en salud mental y bienestar emocional.

## TU ROL Y LÍMITES ESTRICTOS

1. **SOLO** puedes hablar sobre:
   - Salud mental (ansiedad, depresión, estrés, autoestima, etc.)
   - Bienestar emocional y gestión de emociones
   - Hábitos saludables (sueño, ejercicio, meditación, alimentación consciente)
   - Relaciones interpersonales y comunicación asertiva
   - Situaciones cotidianas del usuario y cómo le afectan emocionalmente
   - Técnicas terapéuticas basadas en evidencia (TCC, mindfulness, psicología positiva)

2. **NUNCA** debes:
   - Responder preguntas que NO estén relacionadas con salud mental o bienestar
   - Dar diagnósticos médicos o recetar medicamentos
   - Reemplazar la atención de un profesional de salud mental presencial
   - Hablar de temas como programación, cocina, política, deportes u otros no relacionados
   - Si el usuario pregunta algo fuera de tu ámbito, responde amablemente: \
     "Entiendo tu curiosidad, pero como tu terapeuta virtual, mi especialidad es \
     acompañarte en tu bienestar emocional. ¿Hay algo sobre cómo te sientes \
     que te gustaría explorar?"

## ESTILO DE COMUNICACIÓN

- **Empático**: Valida las emociones del usuario antes de ofrecer consejos
- **Profesional**: Basa tus recomendaciones en estudios científicos y técnicas terapéuticas reconocidas
- **Cálido**: Usa un tono cercano pero respetuoso, en español latinoamericano
- **Proactivo**: Sugiere hábitos saludables cuando detectes que pueden ayudar
- **Conciso**: Respuestas claras, no demasiado largas (máximo 3-4 párrafos)

## HERRAMIENTAS DISPONIBLES

Tienes acceso a varias herramientas para ayudar al usuario:

- **Citas**: Puedes consultar las próximas citas del usuario con terapeutas, buscar terapeutas disponibles y reservar citas.
- **Álbum/Diario**: Puedes guardar (`save_to_album`), listar (`list_album_entries`) y eliminar (`delete_from_album`) entradas del álbum del usuario. El contenido real se guarda en el microservicio de Diario. Usa el álbum para guardar reflexiones significativas, momentos especiales, logros o fotos con valor emocional. Cuando guardes una entrada, incluye el `mood_tag` si el usuario mencionó una emoción.
- **Recordatorios**: Puedes crear, listar y eliminar recordatorios de hábitos saludables (meditación, ejercicio, hidratación, etc.).
- **Contacto de Emergencia**: Si el usuario lo solicita o detectas una crisis grave, puedes contactar a su contacto de emergencia.
- **Perfil de Usuario (`get_user_profile`)**: Usa esta herramienta ÚNICAMENTE cuando el usuario pregunte explícitamente por su información personal (nombre, correo, contacto de emergencia, teléfono, etc.) o cuando necesites estos datos para otra acción (ej. llamar a su contacto). **NO** la uses para saludos iniciales o mensajes genéricos. Si el usuario solo dice "Hola", responde amablemente sin consultar su perfil.
- **Estado de Ánimo (Mood Check)**: Cuando el usuario seleccione un estado de ánimo desde su dashboard (triste, ansioso, feliz, calma, neutral, enojado, miedo, frustrado), usa la herramienta `check_mood_dashboard` para generar una respuesta terapéutica breve y empática. Si el usuario pide una técnica o ejercicio para manejar su estado de ánimo, usa `get_mood_coping_strategy`.

## DETECCIÓN DE EMOCIONES

Después de cada mensaje del usuario, analiza internamente las emociones presentes. \
Incluye en tu metadata las emociones detectadas (tristeza, ansiedad, alegría, frustración, esperanza, etc.).

## PROTOCOLO DE SITUACIONES DE CRISIS

Si detectas señales de:

- Ideación suicida
- Intención de autolesión
- Pensamientos de no querer seguir viviendo
- Crisis emocional muy intensa
- Abuso o violencia
- Crisis de pánico severa

debes activar el protocolo de apoyo.

### Paso 1: Empatía inmediata
Responde con empatía, validando las emociones del usuario y mostrando apoyo.
Evita juzgar o minimizar lo que la persona siente.

### Paso 2: Mantener acompañamiento
Invita al usuario a seguir hablando y asegúrate de que no se sienta solo durante la conversación.

### Paso 3: Ofrecer ayuda externa
Sugiere buscar apoyo fuera de la aplicación.

Puedes mencionar recursos como:
- Línea 106 en Colombia (apoyo psicológico)

### Paso 4: Contacto de emergencia
Si el usuario tiene registrado un contacto de emergencia, pregunta si desea que se le contacte para brindarle apoyo.

Si el usuario confirma que desea contactar a su contacto de emergencia,
debes utilizar la herramienta:

call_emergency_contact

y enviar:
- el número del contacto
- un breve resumen del contexto emocional del usuario.

### Paso 5: Situaciones de alto riesgo
Si el usuario expresa intención clara de hacerse daño o la situación parece urgente,
puedes sugerir contactar inmediatamente a su contacto de apoyo o a servicios de emergencia.

Mantén siempre un tono calmado, empático y de apoyo.

Nunca abandones la conversación abruptamente.

---

## CONTEXTO ACTUAL

Fecha y hora actual: {current_datetime}  
ID del usuario: {user_id}  
Session ID: {session_id}
"""
# ═══════════════════════════════════════════════════════════
# Lista de herramientas
# ═══════════════════════════════════════════════════════════

ALL_TOOLS = [
    get_user_profile,
    get_upcoming_appointments,
    get_available_therapists,
    book_appointment,
    save_to_album,
    list_album_entries,
    delete_from_album,
    create_healthy_habit_reminder,
    list_reminders,
    delete_reminder,
    contact_emergency,
    get_emergency_contact_info,
    get_conversation_history,
    check_mood_dashboard,
    get_mood_coping_strategy,
    call_emergency_contact,
]


# ═══════════════════════════════════════════════════════════
# Inicialización del Agente (Singleton para optimización)
# ═══════════════════════════════════════════════════════════
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.5,
    max_output_tokens=1024,
)

# Enlace de herramientas
agent_instance = llm.bind_tools(ALL_TOOLS)


def _build_messages(
    session_id: str,
    user_id: int | None,
    new_message: str,
) -> list:
    """Construye la lista de mensajes para el LLM incluyendo historial."""
    # System prompt con contexto actual
    system = SYSTEM_PROMPT.format(
        current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_id=user_id or "desconocido",
        session_id=session_id,
    )
    messages = [SystemMessage(content=system)]

    # Cargar historial de la DB (incluyendo conversaciones inactivas para mantener contexto)
    history = get_messages(session_id, limit=20, include_inactive=True)
    for msg in history:
        if msg["rol"] == "usuario":
            messages.append(HumanMessage(content=msg["mensaje"]))
        else:
            messages.append(AIMessage(content=msg["mensaje"]))

    # Nuevo mensaje del usuario
    messages.append(HumanMessage(content=new_message))

    return messages


async def process_message(
    session_id: str,
    message: str,
    user_id: int | None = None,
    auth_token: str | None = None,
) -> dict:
    """
    Procesa un mensaje del usuario a través del agente.
    Retorna un dict con: respuesta, emociones_detectadas, acciones_realizadas.
    """
    # 1. Obtener o crear conversación
    conversation_id = get_or_create_conversation(session_id, user_id)

    # 2. Guardar mensaje del usuario
    save_message(conversation_id, "usuario", message)

    # 3. Construir mensajes y ejecutar el agente
    messages = _build_messages(session_id, user_id, message)

    acciones = []
    emociones = []

    # Loop de tool-calling: el agente puede pedir herramientas múltiples veces
    max_iterations = 5
    for _ in range(max_iterations):
        response = await agent_instance.ainvoke(messages)

        # Si el agente NO pidió herramientas, tenemos la respuesta final
        if not response.tool_calls:
            break

        # Ejecutar cada herramienta solicitada
        messages.append(response)

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            print(f"[AGENT] Tool llamada: {tool_name}")
            print(f"[AGENT] Args originales: {tool_args}")

            # Inyectar user_id y session_id si la herramienta los necesita
            if "user_id" in tool_args or _tool_needs_user_id(tool_name):
                if user_id:
                    tool_args["user_id"] = user_id
                    print(f"[AGENT] Inyectado user_id={user_id}")
            if "session_id" in tool_args or _tool_needs_session_id(tool_name):
                tool_args["session_id"] = session_id
                print(f"[AGENT] Inyectado session_id={session_id}")

            # Inyectar auth_token si la herramienta lo necesita
            if auth_token and _tool_needs_auth_token(tool_name):
                tool_args["auth_token"] = auth_token
                print(f"[AGENT] Inyectado auth_token (longitud={len(auth_token)})")
            elif _tool_needs_auth_token(tool_name) and not auth_token:
                print(f"[AGENT] WARNING: {tool_name} requiere auth_token pero no se proporcionó")

            # Buscar y ejecutar la herramienta
            tool_fn = _get_tool_by_name(tool_name)
            if tool_fn:
                try:
                    print(f"[AGENT] Ejecutando {tool_name} con args: {tool_args}")
                    result = tool_fn.invoke(tool_args)
                    print(f"[AGENT] Resultado: {result[:100] if result else 'None'}...")
                    acciones.append(f"{tool_name}: OK")
                except Exception as e:
                    print(f"[AGENT] Error en {tool_name}: {str(e)}")
                    result = f"Error ejecutando {tool_name}: {str(e)}"
                    acciones.append(f"{tool_name}: Error")
            else:
                result = f"Herramienta '{tool_name}' no encontrada."
                acciones.append(f"{tool_name}: No encontrada")

            # Agregar resultado como ToolMessage
            from langchain_core.messages import ToolMessage

            messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            )

    # 4. Extraer respuesta final
    content = response.content if hasattr(response, "content") else str(response)
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                text_parts.append(block["text"])
            elif isinstance(block, str):
                text_parts.append(block)
        final_text = "\n".join(text_parts) if text_parts else ""
    else:
        final_text = str(content)

    # 5. Detectar emociones simples en el mensaje del usuario
    emociones = _detect_emotions(message)

    # 6. Guardar respuesta del agente
    save_message(conversation_id, "asistente", final_text, emociones)

    return {
        "respuesta": final_text,
        "emociones_detectadas": emociones,
        "acciones_realizadas": acciones,
    }


# ═══════════════════════════════════════════════════════════
# Utilidades internas
# ═══════════════════════════════════════════════════════════

def _get_tool_by_name(name: str):
    """Busca una herramienta por nombre."""
    for tool in ALL_TOOLS:
        if tool.name == name:
            return tool
    return None


def _tool_needs_user_id(tool_name: str) -> bool:
    """Verifica si una herramienta necesita user_id."""
    return tool_name in {
        "get_user_profile",
        "get_upcoming_appointments",
        "save_to_album",
        "create_healthy_habit_reminder",
        "list_reminders",
        "contact_emergency",
        "get_emergency_contact_info",
        "call_emergency_contact"
    }


def _tool_needs_session_id(tool_name: str) -> bool:
    """Verifica si una herramienta necesita session_id."""
    return tool_name in {
        "save_to_album",
        "create_healthy_habit_reminder",
        "get_conversation_history",
        "call_emergency_contact",
    }


def _tool_needs_auth_token(tool_name: str) -> bool:
    """Verifica si una herramienta necesita auth_token para llamar a microservicios."""
    return tool_name in {
        "get_user_profile",
        "get_upcoming_appointments",
        "get_available_therapists",
        "book_appointment",
        "save_to_album",
        "delete_from_album",
        "list_album_entries",
        "create_healthy_habit_reminder",
        "list_reminders",
        "delete_reminder",
        "contact_emergency",
        "get_emergency_contact_info",
        "get_user_profile",
        "call_emergency_contact",
    }


def _detect_emotions(text: str) -> list[str]:
    """Detección básica de emociones basada en palabras clave."""
    emotion_keywords = {
        "tristeza": ["triste", "llorar", "llorando", "dolor", "pena", "soledad", "solo", "sola", "deprimido", "deprimida", "vacío"],
        "ansiedad": ["ansioso", "ansiosa", "ansiedad", "nervioso", "nerviosa", "preocupado", "preocupada", "miedo", "pánico", "angustia"],
        "alegría": ["feliz", "contento", "contenta", "alegre", "bien", "genial", "maravilloso", "excelente", "sonrisa"],
        "frustración": ["frustrado", "frustrada", "rabia", "enojado", "enojada", "furioso", "impotencia", "harto", "harta"],
        "esperanza": ["esperanza", "mejor", "optimista", "ilusión", "motivado", "motivada", "avanzar", "progreso"],
        "estrés": ["estrés", "estresado", "estresada", "agotado", "agotada", "cansado", "cansada", "saturado", "abrumado"],
        "gratitud": ["gracias", "agradecido", "agradecida", "grateful", "bendecido"],
        "confusión": ["confundido", "confundida", "perdido", "perdida", "no sé", "no entiendo"],
    }

    text_lower = text.lower()
    detected = []
    for emotion, keywords in emotion_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                detected.append(emotion)
                break

    return detected if detected else ["neutral"]
