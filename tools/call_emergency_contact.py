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

# Importar para obtener el historial
from database import get_messages

def send_sms_emergency(telefono: str, nombre_usuario: str, contexto: str) -> str:
    """Envía SMS al contacto de emergencia como fallback si la llamada falla."""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=(
                f"Hola, te contactamos desde la aplicación Sanity. "
                f"{nombre_usuario} te registró como su contacto de emergencia. "
                f"Por favor comunícate con él/ella lo antes posible. "
                f"Motivo: {contexto}"
            ),
            from_=TWILIO_PHONE_NUMBER,
            to=telefono
        )
        print(f"[SMS] Enviado correctamente a {telefono} - SID: {message.sid}")
        return "sms_ok"
    except Exception as e:
        print(f"[SMS] Error al enviar SMS: {str(e)}")
        return f"sms_error: {str(e)}"

@tool
def call_emergency_contact(user_id: int, auth_token: str, session_id: str = "") -> str:
    """
    Realiza una llamada al contacto de emergencia del usuario usando IA. Si la llamada falla, envía un SMS como respaldo.
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
        telefono = user_data.get("telefonoContactoEmergencia")
        nombre_usuario = user_data.get("nombre", "Un usuario")
        mensaje_emergencia = user_data.get("mensajeEmergencia", "")

        if not telefono:
            return "⚠️ El usuario no tiene número de contacto de emergencia configurado."

        # Obtener historial reciente para generar el resumen automático
        mensajes_recientes = []
        if session_id:
            try:
                # Obtener los últimos 8 mensajes (suficiente para contexto)
                mensajes_recientes = get_messages(session_id, limit=8, include_inactive=True)
            except Exception as e:
                print(f"[TOOL: call_emergency_contact] Error obteniendo historial: {e}")

        # Generar el resumen automático (IGNORAMOS mensaje_emergencia por petición del usuario)
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

        # Llamada con VAPI
        url = "https://api.vapi.ai/call"

        # VAPI requiere que el número de destino esté en un objeto 'customer'
        # El campo 'phoneNumberId' se usa para el ID del número desde el que se llama
        payload = {
            "assistantId": VAPI_ASSISTANT_ID,
            "customer": {
                "number": telefono,
                "name": nombre_usuario
            },
            "assistantOverrides": {
                 "endCallPhrases": [
                    "así está bien",
                    "hasta luego",
                    "adiós",
                    "chao",
                    "eso es todo",
                    "entendido",
                    "muchas gracias"
                ],
                "variableValues": {
                    "contexto_usuario": contexto,
                    "nombre_usuario": nombre_usuario
                }
            }
        }

        # Si tenemos un ID de número configurado (Twilio/Vapi), lo especificamos
        if VAPI_PHONE_NUMBER_ID:
            payload["phoneNumberId"] = VAPI_PHONE_NUMBER_ID

        headers_vapi = {
            "Authorization": f"Bearer {VAPI_API_KEY}",
            "Content-Type": "application/json"
        }

        print(f"[TOOL: call_emergency_contact] Enviando solicitud a Vapi para {telefono}")
        vapi_response = requests.post(url, json=payload, headers=headers_vapi)
        
        if vapi_response.status_code not in [200, 201]:
            error_data = vapi_response.json() if vapi_response.text else "Sin detalles"
            print(f"[TOOL: call_emergency_contact] Error Vapi ({vapi_response.status_code}): {error_data}")
            return f"❌ No se pudo realizar la llamada. Error del servicio: {vapi_response.status_code}"

        print(f"[TOOL: call_emergency_contact] Vapi Response OK: {vapi_response.status_code}")

        return (
            f"📞 He iniciado una llamada al contacto de emergencia.\n"
            f"Contacto: {contacto}\n"
            f"Teléfono: {telefono}\n\n"
            "Le informaré sobre la situación para que pueda brindarte apoyo."
        )
   # Llamada falló — intentar SMS como respaldo
        error_data = vapi_response.json() if vapi_response.text else "Sin detalles"
        print(f"[TOOL: call_emergency_contact] Error Vapi ({vapi_response.status_code}): {error_data}")
        print(f"[TOOL: call_emergency_contact] Intentando SMS como respaldo...")

        sms_result = send_sms_emergency(telefono, nombre_usuario, contexto)

        if sms_result == "sms_ok":
            return (
                f"📵 No se pudo realizar la llamada, pero se envió un SMS al contacto de emergencia.\n"
                f"Contacto: {contacto}\n"
                f"Teléfono: {telefono}"
            )
        else:
            return (
                f"❌ No se pudo contactar al contacto de emergencia por llamada ni SMS.\n"
                f"Por favor intenta comunicarte manualmente con {contacto} al {telefono}."
            )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return "⚠️ Token inválido. Por favor inicia sesión nuevamente."
        return f"Error al acceder al perfil del usuario: HTTP {e.response.status_code}"

    except Exception as e:
        return f"Error al realizar la llamada de emergencia: {str(e)}"