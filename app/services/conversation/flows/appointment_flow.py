from app.services.conversation.flows.base_flow import BaseFlow

class AppointmentFlow(BaseFlow):
    """Implementa el flujo de agendamiento de citas."""

    async def process_message(self, phone_number: str, message_text: str, conversation_state: dict):
        """Procesa los mensajes dentro del flujo de agendamiento de citas."""
        # Por ahora, solo enviamos un mensaje de bienvenida
        welcome_message = (
            "Bienvenido al sistema de agendamiento de citas. "
            "Aquí podrás reservar, modificar o cancelar tus citas.\n\n"
            "Por el momento, este módulo está en desarrollo."
        )

        return welcome_message, {}, True  # Flujo completado