# app/services/conversation/unknown_handler.py
import random
import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class UnknownIntentHandler:
    """
    Maneja respuestas inteligentes para intenciones no reconocidas.
    Usa contexto conversacional y análisis de palabras clave para guiar al usuario.
    """

    def __init__(self):
        # Contador de mensajes UNKNOWN consecutivos por contacto
        self.unknown_counts = {}
        self.last_unknown_time = {}

        # Variaciones de mensajes según el número de intentos
        self.first_attempt_messages = [
            "Hmm, no estoy seguro de entender completamente lo que necesitas. 🤔",
            "Disculpa, no logré captar exactamente qué buscas. 😅",
            "Perdón, no me queda del todo claro lo que necesitas. 🤷‍♀️",
            "Lo siento, no entendí bien tu mensaje. 😊"
        ]

        self.second_attempt_messages = [
            "Veo que no he logrado entenderte bien. 😔 Déjame ayudarte de otra manera:",
            "Parece que no estoy captando lo que necesitas. 🤨 Te doy algunas opciones:",
            "Creo que no nos estamos entendiendo bien. 😅 ¿Será que alguna de estas opciones te sirve?",
        ]

        self.third_attempt_messages = [
            "Definitivamente no estoy entendiendo lo que necesitas. 😰",
            "Parece que tengo dificultades para ayudarte. 🆘",
            "No logro comprender qué buscas exactamente. 😞",
        ]

        # Palabras clave para sugerir flujos específicos
        self.keyword_hints = {
            'appointment': {
                'keywords': ['cita', 'turno', 'consulta', 'doctor', 'médico', 'agendar', 'reservar', 'programar', 'cancelar', 'reagendar'],
                'suggestion': "¿Quizás necesitas **agendar una cita**? 📅"
            },
            'faq': {
                'keywords': ['precio', 'costo', 'horario', 'servicio', 'información', 'dónde', 'cuánto', 'qué', 'cómo', 'cuál'],
                'suggestion': "¿Tal vez tienes **preguntas sobre nuestros servicios**? 📋"
            },
            'support': {
                'keywords': ['problema', 'error', 'falla', 'no funciona', 'ayuda', 'soporte', 'dificultad'],
                'suggestion': "¿Necesitas **soporte técnico**? 🛠️"
            }
        }

    def handle_unknown_intent(self, message: str, contact_id: str) -> str:
        """
        Genera respuesta inteligente para intenciones no reconocidas.
        """
        # Actualizar contador de intentos UNKNOWN
        attempt_number = self._update_unknown_count(contact_id)

        # Analizar mensaje para sugerir flujo
        suggested_flow = self._analyze_message_for_hints(message)

        logger.info(f"[UNKNOWN] Intento #{attempt_number} para contacto {contact_id}")
        logger.debug(f"[UNKNOWN] Flujo sugerido: {suggested_flow}")

        if attempt_number == 1:
            return self._generate_first_attempt_response(message, suggested_flow)
        elif attempt_number == 2:
            return self._generate_second_attempt_response(suggested_flow)
        elif attempt_number >= 3:
            return self._generate_escalation_response(contact_id)

        return self._generate_fallback_response()

    def _update_unknown_count(self, contact_id: str) -> int:
        """Actualiza y retorna el número de intentos UNKNOWN consecutivos."""
        now = datetime.now()

        # Si han pasado más de 5 minutos, resetear contador
        if contact_id in self.last_unknown_time:
            time_diff = now - self.last_unknown_time[contact_id]
            if time_diff > timedelta(minutes=5):
                self.unknown_counts[contact_id] = 0

        # Incrementar contador
        self.unknown_counts[contact_id] = self.unknown_counts.get(contact_id, 0) + 1
        self.last_unknown_time[contact_id] = now

        return self.unknown_counts[contact_id]

    def _analyze_message_for_hints(self, message: str) -> str:
        """Analiza el mensaje para sugerir el flujo más probable."""
        message_lower = message.lower()

        for flow, data in self.keyword_hints.items():
            for keyword in data['keywords']:
                if keyword in message_lower:
                    logger.debug(f"[UNKNOWN] Keyword '{keyword}' encontrada, sugiriendo {flow}")
                    return data['suggestion']

        return ""

    def _generate_first_attempt_response(self, message: str, suggested_flow: str) -> str:
        """Genera respuesta para el primer intento fallido."""

        # Seleccionar mensaje base aleatorio
        base_message = random.choice(self.first_attempt_messages)

        # Construir respuesta
        if suggested_flow:
            # Tenemos una sugerencia específica
            response = f"{base_message}\n\n{suggested_flow}"
            response += "\n\nO también puedo ayudarte con:\n"
        else:
            # No hay sugerencia específica
            response = f"{base_message}\n\n¿En qué puedo ayudarte?"
            response += "\n\nPuedo colaborarte con:\n"

        # Agregar opciones
        response += "📋 Preguntas frecuentes\n"
        response += "📅 Agendar una cita\n"
        response += "🛠️ Soporte técnico\n"
        response += "💬 Finalizar conversación\n\n"
        response += "Solo dime qué necesitas. 😊"

        return response

    def _generate_second_attempt_response(self, suggested_flow: str) -> str:
        """Genera respuesta para el segundo intento fallido."""

        base_message = random.choice(self.second_attempt_messages)

        response = f"{base_message}\n\n"

        if suggested_flow:
            response += f"{suggested_flow}\n\n"

        response += "Escribe una de estas opciones:\n"
        response += "• **\"Preguntas\"** para dudas generales 📋\n"
        response += "• **\"Cita\"** para agendamiento 📅\n"
        response += "• **\"Soporte\"** para problemas técnicos 🛠️\n"
        response += "• **\"Finalizar\"** para terminar 💬\n\n"
        response += "¿Cuál te sirve mejor?"

        return response

    def _generate_escalation_response(self, contact_id: str) -> str:
        """Genera respuesta de escalación tras múltiples fallos."""

        base_message = random.choice(self.third_attempt_messages)

        response = f"{base_message}\n\n"
        response += "Te voy a conectar con un miembro de nuestro equipo humano "
        response += "que podrá ayudarte mejor. 👩‍💼\n\n"
        response += "Por favor, describe brevemente lo que necesitas y "
        response += "alguien se comunicará contigo pronto.\n\n"
        response += "¡Gracias por tu paciencia! 🙏"

        # Resetear contador después de escalación
        self.unknown_counts[contact_id] = 0

        return response

    def _generate_fallback_response(self) -> str:
        """Respuesta de seguridad por si algo falla."""
        return (
            "¡Hola! ¿En qué puedo ayudarte hoy?\n\n"
            "Puedo ayudarte con:\n"
            "📋 Preguntas frecuentes\n"
            "📅 Agendar una cita\n"
            "🛠️ Soporte técnico\n"
            "💬 Finalizar conversación\n\n"
            "Solo dime qué necesitas."
        )

    def reset_unknown_count(self, contact_id: str):
        """Resetea el contador cuando el usuario tiene éxito."""
        if contact_id in self.unknown_counts:
            del self.unknown_counts[contact_id]
        if contact_id in self.last_unknown_time:
            del self.last_unknown_time[contact_id]

    def get_unknown_stats(self, contact_id: str) -> Dict:
        """Obtiene estadísticas para debugging."""
        return {
            'unknown_count': self.unknown_counts.get(contact_id, 0),
            'last_unknown': self.last_unknown_time.get(contact_id),
            'escalation_needed': self.unknown_counts.get(contact_id, 0) >= 3
        }