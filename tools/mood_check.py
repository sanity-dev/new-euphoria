"""
Sanity Agent – Tool: Mood Check
Genera respuestas terapéuticas breves para estados de ánimo del dashboard.
"""

from __future__ import annotations

from langchain_core.tools import tool


# Respuestas predefinidas por estado de ánimo (basadas en técnicas terapéuticas)
MOOD_RESPONSES = {
    "triste": [
        "Entiendo que te sientes triste. Es válido sentirse así. Permítete experimentar esta emoción sin juzgarla. Estoy aquí para acompañarte.",
        "La tristeza es una emoción natural que nos invita a reflexionar. Respira profundo y recuerda que no estás solo. Cuenta conmigo.",
        "Reconocer la tristeza es el primer paso. Date permiso de sentir, pero también recuerda que esta emoción pasará. Estoy contigo.",
    ],
    "ansioso": [
        "La ansiedad puede ser abrumadora, pero es temporal. Prueba respirar profundamente: inhala en 4, mantén 4, exhala en 6. Estoy aquí.",
        "Entiendo que te sientes ansioso. Recuerda que los pensamientos ansiosos no son hechos. Respira conmigo: estás a salvo en este momento.",
        "La ansiedad es una señal de que algo te preocupa. Vamos a abordarlo juntos. Primero, respira profundo. Estoy aquí para escucharte.",
    ],
    "feliz": [
        "¡Qué alegría saber que te sientes feliz! Disfruta este momento, reconócelo y guárdalo en tu corazón. La felicidad también se cultiva.",
        "Me llena de alegría saber que estás bien. Aprovecha esta energía positiva para hacer algo que te haga sentir aún mejor.",
        "¡Excelente! La felicidad es contagiosa. Comparte esta energía con alguien especial o dedícate a hacer lo que amas.",
    ],
    "calma": [
        "La calma es un estado preciado. Disfruta este momento de paz interior y recárgate. Estás en equilibrio y eso es maravilloso.",
        "Qué hermoso que te sientas en calma. Este es un buen momento para practicar la gratitud o simplemente ser consciente del presente.",
        "La tranquilidad que sientes es un regalo. Tómate un momento para apreciarlo y anclarlo en tu memoria para momentos difíciles.",
    ],
    "neutral": [
        "Los días neutrales también son válidos. No siempre necesitamos estar eufóricos. La estabilidad emocional es un logro.",
        "Estar en neutral puede ser un buen punto de partida. ¿Hay algo pequeño que puedas hacer hoy para cuidar de ti?",
        "La neutralidad emocional nos da claridad. Es un buen momento para reflexionar o simplemente estar presente.",
    ],
    "enojado": [
        "El enojo es una emoción válida que nos señala límites. Respira antes de actuar. Estoy aquí para escucharte sin juzgar.",
        "Entiendo que te sientas enojado. El enojo nos protege, pero también podemos aprender de él. ¿Qué te está diciendo esta emoción?",
        "El enojo es energía. Puedes transformarla en algo constructivo. Primero, respira. Luego, exploremos juntos qué lo causó.",
    ],
    "miedo": [
        "El miedo nos protege del peligro, pero a veces es exagerado. Respira profundo. Estás a salvo en este momento. Estoy contigo.",
        "Entiendo que tengas miedo. Es válido. Vamos a explorar juntos qué lo causa y cómo puedes afrontarlo. No estás solo.",
        "El miedo puede paralizarnos, pero también nos prepara. Reconócelo, pero no dejes que te controle. Estoy aquí para apoyarte.",
    ],
    "frustrado": [
        "La frustración es señal de que te importa. Respira profundo. Vamos a explorar qué puedes controlar y qué no. Estoy aquí.",
        "Entiendo que te sientas frustrado. Es válido cuando las cosas no salen como esperamos. Date crédito por intentarlo.",
        "La frustración puede ser motivación disfrazada. ¿Qué puedes aprender de esta situación? Estoy aquí para apoyarte.",
    ],
}

# Respuesta por defecto si el mood no está reconocido
DEFAULT_RESPONSE = "Gracias por compartir cómo te sientes. Todas las emociones son válidas y temporales. Estoy aquí para acompañarte en este proceso."


@tool
def check_mood_dashboard(mood: str, user_id: int | None = None) -> str:
    """
    Genera una respuesta terapéutica breve para un estado de ánimo indicado 
    desde el dashboard del usuario.
    
    Usa esta herramienta cuando el usuario seleccione un estado de ánimo 
    (triste, ansioso, feliz, calma, neutral, enojado, miedo, frustrado) 
    desde el dashboard principal de la aplicación.
    
    Args:
        mood: El estado de ánimo del usuario (en español, minúsculas).
        user_id: ID del usuario (opcional, para personalización futura).
    
    Returns:
        Una respuesta terapéutica empática y breve (máximo 2-3 oraciones).
    """
    import random
    
    mood_lower = mood.lower().strip()
    
    # Buscar respuesta específica o usar default
    responses = MOOD_RESPONSES.get(mood_lower, [DEFAULT_RESPONSE])
    
    # Seleccionar respuesta aleatoria para variedad
    selected_response = random.choice(responses)
    
    return selected_response


@tool
def get_mood_coping_strategy(mood: str) -> str:
    """
    Obtiene una estrategia de afrontamiento específica para el estado de ánimo.
    
    Usa esta herramienta cuando el usuario pida una técnica o ejercicio 
    para manejar su estado de ánimo actual.
    
    Args:
        mood: El estado de ánimo del usuario.
    
    Returns:
        Una estrategia de afrontamiento concreta y aplicable.
    """
    coping_strategies = {
        "triste": "Prueba escribir 3 cosas por las que estás agradecido hoy, aunque sean pequeñas. La gratitud puede ayudar a cambiar gradualmente tu perspectiva.",
        "ansioso": "Prueba la técnica 5-4-3-2-1: identifica 5 cosas que ves, 4 que puedes tocar, 3 que escuchas, 2 que hueles y 1 que saboreas. Esto te ancla al presente.",
        "feliz": "Comparte esta alegría con alguien especial o escribe en tu diario qué te hizo sentir así. Guardar estos momentos te ayudará en días difíciles.",
        "calma": "Aprovecha este estado para practicar 5 minutos de mindfulness o meditación. Es el momento ideal para cultivar la paz interior.",
        "neutral": "Es un buen día para establecer una pequeña meta o hábito positivo. ¿Qué te gustaría mejorar hoy, aunque sea un 1%?",
        "enojado": "Antes de reaccionar, escribe lo que sientes en un papel. Luego rómpelo. Esto libera la emoción sin lastimar a nadie.",
        "miedo": "Haz una lista: ¿qué es real y qué es imaginario en lo que temes? Enfócate en lo que puedes controlar, no en lo incierto.",
        "frustrado": "Divide lo que te frustra en partes pequeñas. ¿Cuál es el primer paso mínimo que puedes dar? Celebra cada pequeño progreso.",
    }
    
    return coping_strategies.get(mood.lower().strip(), 
        "Respira profundamente tres veces. Luego, pregúntate: ¿qué necesito en este momento para sentirme un poco mejor?")
