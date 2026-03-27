import requests
import httpx
import os
from langchain_core.tools import tool
from twilio.rest import Client

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")
VAPI_PHONE_NUMBER_ID = os.getenv("VAPI_PHONE_NUMBER_ID")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL", "http://localhost:8081")

from database import get_messages

def send_sms_emergency(telefono_contacto: str, nombre_usuario: str, telefono_usuario: str) -> str:
    """Envía SMS al contacto de emergencia."""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Formatear el teléfono del usuario para mostrarlo en el mensaje
        tel_formateado = telefono_usuario if telefono_usuario else "No disponible"
        
        message = client.messages.create(
            body=(
                f"Sanity: {nombre_usuario} necesita tu apoyo. "
                f"Su número es: {tel_formateado}. "
                f"Contáctalo/a lo antes posible. "
                f"Línea crisis Colombia: 106"
            ),
            from_=TWILIO_PHONE_NUMBER,
            to=telefono_contacto
        )
        print(f"[SMS] Enviado correctamente a {telefono_contacto} - SID: {message.sid}")
        return "sms_ok"
    except Exception as e:
        print(f"[SMS] Error al enviar SMS: {str(e)}")
        return f"sms_error: {str(e)}"

@tool
def call_emergency_contact(user_id: int, auth_token: str, session_id: str = "") -> str:
    """
    Realiza una llamada al contacto de emergencia del usuario usando IA
    y envía un SMS siempre, sin importar si la llamada fue exitosa o no.
    """

    if not auth_token:
        return "⚠️ No se proporcionó token de autenticación."

    try:
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Obtener datos del usuario
        response = httpx.get(
            f"{USERS_SERVICE_URL}/api/personas/{user_id}",
            headers=headers,
            timeout=10.0,
        )
        response.raise_for_status()

        user_data = response.json()

        contacto = user_data.get("contactoEmergencia")
        telefono_emergencia = user_data.get("telefonoContactoEmergencia")
        nombre_usuario = user_data.get("nombre", "Un usuario")
        telefono_usuario = user_data.get("telefono")

        if not telefono_emergencia:
            return "⚠️ El usuario no tiene número de contacto de emergencia configurado."

        # Obtener historial reciente para generar el resumen automático
        mensajes_recientes = []
        if session_id:
            try:
                mensajes_recientes = get_messages(session_id, limit=8, include_inactive=True)
            except Exception as e:
                print(f"[TOOL: call_emergency_contact] Error obteniendo historial: {e}")

        # Generar contexto
        if mensajes_recientes:
            historial_texto = "\n".join([f"- {m['rol'].capitalize()}: {m['mensaje']}" for m in mensajes_recientes])
            contexto = (
                f"El usuario {nombre_usuario} está usando la app de salud mental Sanity. "
                f"Sus últimos mensajes muestran lo siguiente:\n{historial_texto}\n\n"
                "Por favor, informa al contacto sobre su estado actual con base en esto."
            )
        else:
            contexto = (
                f"{nombre_usuario} podría estar pasando por un momento emocional difícil "
                f"y necesita apoyo de su contacto de confianza."
            )

        # ── 1. LLAMADA CON VAPI ──────────────────────────────────────────────
        llamada_ok = False
        llamada_detalle = ""

        try:
            url = "https://api.vapi.ai/call"
            payload = {
                "assistantId": VAPI_ASSISTANT_ID,
                "customer": {
                    "number": telefono_emergencia,
                    "name": nombre_usuario
                },
                "assistantOverrides": {
                    "endCallPhrases": [
                        "así está bien", "hasta luego", "adiós",
                        "chao", "eso es todo", "entendido", "muchas gracias"
                    ],
                    "variableValues": {
                        "contexto_usuario": contexto,
                        "nombre_usuario": nombre_usuario
                    }
                }
            }

            if VAPI_PHONE_NUMBER_ID:
                payload["phoneNumberId"] = VAPI_PHONE_NUMBER_ID

            headers_vapi = {
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json"
            }

            print(f"[TOOL: call_emergency_contact] Enviando solicitud a Vapi para {telefono_emergencia}")
            vapi_response = requests.post(url, json=payload, headers=headers_vapi)

            if vapi_response.status_code in [200, 201]:
                llamada_ok = True
                print(f"[TOOL: call_emergency_contact] Vapi Response OK: {vapi_response.status_code}")
            else:
                error_data = vapi_response.json() if vapi_response.text else "Sin detalles"
                llamada_detalle = f"Error Vapi ({vapi_response.status_code}): {error_data}"
                print(f"[TOOL: call_emergency_contact] {llamada_detalle}")

        except Exception as e:
            llamada_detalle = f"Excepción durante la llamada: {str(e)}"
            print(f"[TOOL: call_emergency_contact] {llamada_detalle}")

        # ── 2. SMS SIEMPRE ───────────────────────────────────────────────────
        print(f"[TOOL: call_emergency_contact] Enviando SMS a {telefono_emergencia} (siempre)")
        sms_result = send_sms_emergency(telefono_emergencia, nombre_usuario, telefono_usuario)

        # ── 3. RESPUESTA COMBINADA ───────────────────────────────────────────
        lineas = [f"Contacto: {contacto}", f"Teléfono: {telefono_emergencia}", ""]

        if llamada_ok:
            lineas.insert(0, "📞 Llamada iniciada correctamente.")
        else:
            lineas.insert(0, f"📵 No se pudo iniciar la llamada. {llamada_detalle}")

        if sms_result == "sms_ok":
            lineas.append("📩 SMS enviado correctamente.")
        else:
            lineas.append(f"⚠️ No se pudo enviar el SMS. {sms_result}")

        return "\n".join(lineas)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return "⚠️ Token inválido. Por favor inicia sesión nuevamente."
        return f"Error al acceder al perfil del usuario: HTTP {e.response.status_code}"

    except Exception as e:
        return f"Error al realizar la llamada de emergencia: {str(e)}"