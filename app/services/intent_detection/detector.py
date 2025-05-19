import logging
from enum import Enum, auto

logger = logging.getLogger(__name__)

class Intent(Enum):
    """Enum para los tipos de intención."""
    UNKNOWN = auto()
    FAQ = auto()
    APPOINTMENT = auto()
    END_CONVERSATION = auto()

class IntentDetector:
    """
    Detector de intenciones basado en palabras clave.

    En implementaciones futuras podría usarse NLP avanzado o un modelo de IA.
    """

    def __init__(self):
        # Diccionario de palabras clave para cada intención
        self.intent_keywords = {
            Intent.FAQ: ["pregunta", "duda", "ayuda", "información", "info", "faq",
                         "preguntas", "frecuentes", "cómo", "qué", "cuál", "cuando",
                         "cuándo", "por qué"],
            Intent.APPOINTMENT: ["cita", "agendar", "agenda", "reservar", "reserva",
                               "turno", "hora", "disponibilidad", "horario", "fecha",
                               "programar", "programación"],
            Intent.END_CONVERSATION: ["gracias", "adiós", "chao", "hasta luego",
                                    "nos vemos", "bye", "terminar", "finalizar",
                                    "fin", "salir"]
        }

    def detect_intent(self, message_text: str) -> Intent:
        """
        Detecta la intención a partir del texto del mensaje.

        Args:
            message_text: Texto del mensaje a analizar.

        Returns:
            Intent: La intención detectada.
        """
        if not message_text:
            return Intent.UNKNOWN

        # Convertir el mensaje a minúsculas para comparación
        text_lower = message_text.lower()

        # Buscar palabras clave en el mensaje
        for intent, keywords in self.intent_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    logger.info(f"Intención detectada: {intent} por palabra clave: {keyword}")
                    return intent

        # Si no se encuentra ninguna palabra clave, devolver UNKNOWN
        return Intent.UNKNOWN