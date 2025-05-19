from app.services.conversation.flows.base_flow import BaseFlow

class FAQFlow(BaseFlow):
    """Implementa el flujo de preguntas frecuentes."""

    async def process_message(self, phone_number: str, message_text: str, conversation_state: dict):
        """Procesa los mensajes dentro del flujo de preguntas frecuentes."""
        # Por ahora, solo enviamos un mensaje de bienvenida
        welcome_message = (
            "Bienvenido al sistema de preguntas frecuentes. "
            "Aquí podrás encontrar respuestas a las dudas más comunes.\n\n"
            "Por el momento, este módulo está en desarrollo."
        )

        return welcome_message, {}, True  # Flujo completado