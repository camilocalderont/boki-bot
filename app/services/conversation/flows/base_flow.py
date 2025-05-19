from abc import ABC, abstractmethod

class BaseFlow(ABC):
    """
    Clase base para los flujos de conversación.
    Todos los flujos específicos deben heredar de esta clase.
    """

    @abstractmethod
    async def process_message(self, phone_number: str, message_text: str, conversation_state: dict):
        """
        Procesa un mensaje dentro del flujo y actualiza el estado de la conversación.

        Args:
            phone_number: Número de teléfono del usuario.
            message_text: Texto del mensaje recibido.
            conversation_state: Estado actual de la conversación.

        Returns:
            tuple: (respuesta, nuevo_estado, flujo_completo)
                - respuesta: Texto de respuesta para el usuario.
                - nuevo_estado: Estado actualizado de la conversación.
                - flujo_completo: Booleano que indica si el flujo ha terminado.
        """
        pass