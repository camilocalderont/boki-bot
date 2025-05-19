from app.services.conversation.flows.base_flow import BaseFlow

class EndConversationFlow(BaseFlow):
    """Implementa el flujo de fin de conversación."""

    async def process_message(self, phone_number: str, message_text: str, conversation_state: dict):
        """Procesa los mensajes dentro del flujo de fin de conversación."""
        # Mensaje de despedida
        farewell_message = (
            "¡Gracias por contactarnos! Esperamos haberte ayudado. "
            "Si necesitas algo más, no dudes en escribirnos nuevamente. "
            "¡Hasta pronto!"
        )

        return farewell_message, {}, True  # Flujo completado