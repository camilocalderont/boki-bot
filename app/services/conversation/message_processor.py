import logging
import uuid
from typing import Optional
from app.services.external import BokiApi

logger = logging.getLogger(__name__)

class MessageProcessor:
    """
    Responsabilidad única: Validar duplicados y registrar mensajes.
    """

    def __init__(self, boki_api: BokiApi = None):
        """
        Inicializa el procesador de mensajes.
        
        Args:
            boki_api: Instancia de BokiApi. Si es None, se crea una nueva.
        """
        self.boki_api = boki_api or BokiApi()

    async def is_duplicate_message(self, message_id: str) -> bool:
        """
        Verifica si un mensaje ya fue procesado.
        
        Args:
            message_id: ID del mensaje de WhatsApp
            
        Returns:
            bool: True si es duplicado, False si no
        """
        try:
            if not message_id:
                return False
                
            return await self.boki_api.is_message_processed(message_id)
            
        except Exception as e:
            logger.error(f"❌ Error verificando duplicado: {e}")
            return False

    async def log_incoming_message(self, contact_id: str, message_id: str, message_text: str) -> bool:
        """
        Registra un mensaje entrante.
        
        Args:
            contact_id: ID del contacto
            message_id: ID del mensaje
            message_text: Contenido del mensaje
            
        Returns:
            bool: True si se registró correctamente
        """
        try:
            # Contexto básico para mensaje entrante
            flow_context = {"flow": "general", "step": "incoming"}
            
            result = await self.boki_api.log_incoming_message(
                contact_id, message_id, message_text, flow_context
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error registrando mensaje entrante: {e}")
            return False

    async def log_outgoing_message(self, contact_id: str, response_text: str) -> bool:
        """
        Registra un mensaje saliente.
        
        Args:
            contact_id: ID del contacto
            response_text: Texto de la respuesta
            
        Returns:
            bool: True si se registró correctamente
        """
        try:
            # Generar ID único para la respuesta
            response_id = f"bot_{uuid.uuid4().hex[:8]}"
            
            # Contexto básico para mensaje saliente
            flow_context = {"flow": "general", "step": "response"}
            
            result = await self.boki_api.log_outgoing_message(
                contact_id, response_id, response_text, flow_context
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error registrando mensaje saliente: {e}")
            return False