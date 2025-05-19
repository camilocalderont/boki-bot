import logging
from app.services.conversation.flows.base_flow import BaseFlow
from app.services.boki_api import BokiApi, BokiApiError
from app.models.client import ClientCreate
from pydantic import ValidationError

logger = logging.getLogger(__name__)

class RegistrationFlow(BaseFlow):
    """Implementa el flujo de registro de usuario."""

    def __init__(self):
        self.nestjs_client = BokiApi()

    async def process_message(self, phone_number: str, message_text: str, conversation_state: dict):
        """
        Procesa los mensajes dentro del flujo de registro.

        El flujo pasa por los siguientes pasos:
        1. Solicitar ID
        2. Solicitar nombre
        3. Registrar
        """
        # Si es la primera vez, inicializar el estado
        if "step" not in conversation_state:
            conversation_state["step"] = "waiting_id"
            conversation_state["data"] = {}

        current_step = conversation_state["step"]
        data = conversation_state["data"]

        # Proceso según el paso actual
        if current_step == "waiting_id":
            # Validar ID
            id_number = message_text.strip()
            if not id_number:
                return "Por favor, proporciona un número de documento válido:", conversation_state, False

            # Guardar ID y avanzar al siguiente paso
            data["VcIdentificationNumber"] = id_number
            conversation_state["step"] = "waiting_name"

            return "Gracias. Ahora, por favor proporciona tu nombre completo:", conversation_state, False

        elif current_step == "waiting_name":
            # Validar nombre
            name = message_text.strip()
            if not name:
                return "Por favor, proporciona un nombre válido:", conversation_state, False

            # Guardar nombre y preparar registro
            data["VcFirstName"] = name
            data["VcPhone"] = phone_number

            # Intentar registrar al usuario
            try:
                # Validar datos con Pydantic
                client_data = ClientCreate(**data)

                # Crear cliente en la API
                await self.nestjs_client.create_client(client_data.dict())

                # Flujo completado exitosamente
                return (
                    "¡Registro exitoso! Bienvenido a nuestro servicio. "
                    "¿En qué podemos ayudarte hoy? Puedes hacer preguntas o agendar una cita.",
                    {}, True  # Limpiar estado y marcar como completado
                )

            except ValidationError as e:
                logger.error(f"Error de validación: {str(e)}")
                # Volver a solicitar datos
                conversation_state["step"] = "waiting_id"
                conversation_state["data"] = {}
                return (
                    "Los datos proporcionados no son válidos. Por favor, "
                    "comencemos de nuevo. Proporciona tu número de documento:",
                    conversation_state, False
                )

            except BokiApiError as e:
                logger.error(f"Error al crear cliente: {str(e)}")
                return (
                    "Hubo un problema al registrar tus datos. Por favor, "
                    "intenta nuevamente más tarde o contacta a soporte.",
                    {}, True  # Terminar flujo con error
                )