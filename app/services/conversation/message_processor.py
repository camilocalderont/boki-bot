import logging
import uuid
from typing import Optional, Dict, Any
from app.services.external import BokiApi

logger = logging.getLogger(__name__)

class MessageProcessor:
    """
    Responsabilidad única: Procesar y validar mensajes entrantes.
    """

    def __init__(self, boki_api: BokiApi = None):
        """
        Inicializa el procesador de mensajes.
        
        Args:
            boki_api: Instancia de BokiApi. Si es None, se crea una nueva.
        """
        self.boki_api = boki_api or BokiApi()

    async def process_incoming_message(self, phone_number: str, message_text: str, message_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Procesa y valida un mensaje entrante.
        Retorna diccionario con toda la información necesaria para el routing.
        """
        try:
            # 1. Verificar duplicados
            if message_id and await self.boki_api.is_message_processed(message_id):
                return {"is_duplicate": True}

            # 2. Obtener/crear contacto
            contact = await self.boki_api.get_or_create_contact(phone_number)
            if not contact or not contact.get("_id"):
                return {"error": "contact_error"}

            contact_id = contact["_id"]

            # 3. Verificar registro del usuario
            client = await self.boki_api.get_client_by_phone(phone_number)
            is_registered = client is not None

            # 4. Obtener estado de conversación
            # conversation_state = await self.boki_api.get_conversation_state(contact_id)

            # # 5. Registrar mensaje entrante
            # if message_id:
            #     flow_context = self._extract_flow_context(conversation_state)
            #     await self.boki_api.log_incoming_message(
            #         contact_id, message_id, message_text, flow_context
            #     )

            return {
                "contact_id": contact_id,
                "phone_number": phone_number,
                "message_text": message_text,
                "message_id": message_id,
                "is_registered": is_registered,
                # "conversation_state": conversation_state,
                "is_duplicate": False,
                "error": None
            }

        except Exception as e:
            return {"error": "processing_error"}

    async def log_outgoing_message(self, contact_id: str, response: str) -> None:
        """Registra la respuesta enviada al usuario."""
        try:
            response_id = f"bot_{uuid.uuid4().hex[:8]}"
            updated_state = await self.boki_api.get_conversation_state(contact_id)
            updated_context = self._extract_flow_context(updated_state)
            
            await self.boki_api.log_outgoing_message(
                contact_id, response_id, response, updated_context
            )
        except Exception as e:
            return {"error": "logging_error"}

    def _extract_flow_context(self, conversation_state: Optional[Dict]) -> Dict[str, str]:
        """Extrae el contexto del flujo del estado de conversación."""
        if not conversation_state:
            return {"flow": "general", "step": "initial"}

        state_data = conversation_state.get("_doc", conversation_state)
        flow = state_data.get("flow", "general")
        step = state_data.get("state", {}).get("step", "initial")

        return {"flow": flow, "step": step}