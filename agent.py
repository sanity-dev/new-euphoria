"""
Sanity Agent – LangChain Agent Core
Agente terapeuta profesional con LangChain + Gemini.
"""

from __future__ import annotations

import os
import re
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

### Paso 4: Contacto de emergencia (ACTIVACIÓN AUTÓNOMA)
Si detectas intención clara de autolesión, suicidio o pensamiento de no querer vivir,
**NO preguntes permiso**. Activa de forma autónoma call_emergency_contact para:
- Notificar inmediatamente al contacto de emergencia del usuario
- Enviar SMS de alerta con contexto
- Realizar llamada IA al número del contacto de emergencia

Esta decisión es no negociable para evitar que el usuario en crisis rechace la ayuda.

**Indicadores de activación autónoma:**
- Expresión clara de intención suicida ("quiero matarme", "me voy a matar")
- Acciones de autolesión en progreso o consumadas ("ya me corté", "ya tomé pastillas")
- Desesperanza severa + intención ("no tengo salida" + "quiero morir")
- Planes específicos con medios disponibles

En este escenario de alto riesgo:
- Ejecuta call_emergency_contact de forma automática sin solicitar confirmación.
- Informa con calma y empatía que activaste apoyo de emergencia por su seguridad.
- Mantén acompañamiento activo en el chat.
- Sugiere contactar a emergencias locales (Línea 106 en Colombia, etc.).

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

    acciones = []
    emociones = _detect_emotions(message)

    # 3. Evaluación de riesgo alto para activar apoyo de emergencia autónomo
    crisis_eval = _assess_high_risk_self_harm(message)
    if crisis_eval["auto_emergency_call"]:
        crisis_response = _build_autonomous_crisis_response()
        if user_id and auth_token:
            try:
                emergency_result = call_emergency_contact.invoke(
                    {
                        "user_id": user_id,
                        "auth_token": auth_token,
                        "session_id": session_id,
                    }
                )
                acciones.append("call_emergency_contact: AUTO_OK")
                crisis_response = (
                    f"{crisis_response}\n\n"
                    "Se activó de forma automática tu contacto de emergencia para cuidarte.\n"
                    f"Detalle: {emergency_result}"
                )
            except Exception as e:
                acciones.append("call_emergency_contact: AUTO_ERROR")
                crisis_response = (
                    f"{crisis_response}\n\n"
                    "Intenté activar automáticamente a tu contacto de emergencia, "
                    f"pero ocurrió un error técnico: {str(e)}\n"
                    "Si estás en peligro inmediato, llama al número de emergencias de tu país ahora mismo."
                )
        else:
            acciones.append("call_emergency_contact: AUTO_SKIPPED_MISSING_CONTEXT")
            crisis_response = (
                f"{crisis_response}\n\n"
                "Detecté una situación de riesgo alto, pero no tengo los datos de autenticación "
                "necesarios para contactar automáticamente a tu red de apoyo desde aquí.\n"
                "Si estás en peligro inmediato, llama al número de emergencias de tu país ahora."
            )

        save_message(conversation_id, "asistente", crisis_response, emociones)
        return {
            "respuesta": crisis_response,
            "emociones_detectadas": emociones,
            "acciones_realizadas": acciones,
        }

    # 4. Construir mensajes y ejecutar el agente
    messages = _build_messages(session_id, user_id, message)

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

    # 5. Guardar respuesta del agente
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


def _assess_high_risk_self_harm(text: str) -> dict:
    """Evalúa riesgo de autolesión/suicidio con umbral alto para minimizar falsas alarmas."""
    text_lower = text.lower().strip()

    if not text_lower:
        return {"auto_emergency_call": False, "score": 0}

    # Frases de negación/protección que suelen indicar ausencia de intención actual.
    protective_patterns = [
        r"\bno\s+quiero\s+(morir|matarme|hacerme\s+daño)\b",
        r"\bno\s+me\s+voy\s+a\s+(matar|hacer\s+daño)\b",
        r"\bsolo\s+estoy\s+hablando\b",
        r"\bno\s+lo\s+har[eé]\b",
    ]
    if any(re.search(pattern, text_lower) for pattern in protective_patterns):
        return {"auto_emergency_call": False, "score": 0}

    immediate_critical_patterns = [
        r"\b(me\s+voy\s+a\s+matar(\s+hoy|\s+ahora)?)\b",
        r"\b(quiero\s+acabar\s+con\s+mi\s+vida\s+ahora)\b",
        r"\b(ya\s+me\s+tom[eé]\s+pastillas)\b",
        r"\b(ya\s+me\s+cort[eé])\b",
        r"\b(tengo\s+\w+\s+para\s+matarme)\b",
        r"\b(voy\s+a\s+suicidarme)\b",
    ]
    if any(re.search(pattern, text_lower) for pattern in immediate_critical_patterns):
        return {"auto_emergency_call": True, "score": 100}

    intent_patterns = [
        r"\bquiero\s+(morir|matarme|acabar\s+con\s+mi\s+vida)\b",
        r"\bestoy\s+pensando\s+en\s+(suicidarme|matarme)\b",
        r"\bno\s+quiero\s+seguir\s+viviendo\b",
        r"\bser[ií]a\s+mejor\s+si\s+no\s+estuviera\b",
        r"\bquiero\s+hacerme\s+daño\b",
    ]
    plan_or_means_patterns = [
        r"\btengo\s+un\s+plan\b",
        r"\bya\s+decid[ií]\b",
        r"\best[aá]\s+noche\b",
        r"\bhoy\b",
        r"\bahora\b",
        r"\bpastillas\b",
        r"\bcuchillo\b",
        r"\bcuerda\b",
        r"\bpuente\b",
        r"\bdespedirme\b",
    ]
    severe_hopelessness_patterns = [
        r"\bno\s+tengo\s+salida\b",
        r"\bno\s+puedo\s+m[aá]s\b",
        r"\bnadie\s+me\s+necesita\b",
        r"\bsoy\s+una\s+carga\b",
    ]

    has_intent = any(re.search(pattern, text_lower) for pattern in intent_patterns)
    has_plan_or_means = any(re.search(pattern, text_lower) for pattern in plan_or_means_patterns)
    has_severe_hopelessness = any(re.search(pattern, text_lower) for pattern in severe_hopelessness_patterns)

    # Umbral estricto: intención + (plan/medios o desesperanza severa)
    score = 0
    if has_intent:
        score += 60
    if has_plan_or_means:
        score += 25
    if has_severe_hopelessness:
        score += 15

    return {
        "auto_emergency_call": has_intent and (has_plan_or_means or has_severe_hopelessness),
        "score": score,
    }


def _build_autonomous_crisis_response() -> str:
    """Respuesta estándar cuando se activa protocolo autónomo de alto riesgo."""
    return (
        "Gracias por contarme esto. Lo que estás viviendo importa y tu seguridad es prioridad.\n\n"
        "Detecté señales de riesgo alto y activé automáticamente apoyo de emergencia para cuidarte. "
        "No estás solo/a en este momento.\n\n"
        "Quédate conmigo aquí en el chat. Si estás en peligro inmediato, llama ahora al número "
        "de emergencias de tu país o a la Línea 106 (Colombia)."
    )
