import logging
from typing import Dict, Optional
from .base_client import BaseClient

logger = logging.getLogger(__name__)

class MessagesApi(BaseClient):
    """
    Cliente para gestión de historial de mensajes.
    Responsabilidad única: operaciones de mensajes entrantes y salientes.
    """

    async def is_message_processed(self, message_id: str) -> bool:
        """
        Verifica si un mensaje ya fue procesado.
        
        Args:
            message_id: ID del mensaje de WhatsApp
            
        Returns:
            bool: True si ya fue procesado
        """
        try:
            url = f"message-history/whatsapp/{message_id}"
            response = await self._make_request("GET", url)

            if response.status_code == 200:
                result = response.json().get("data")
                is_processed = result is not None
                logger.debug(f"[MESSAGES] Mensaje {message_id} procesado: {is_processed}")
                return is_processed
            elif response.status_code == 404:
                logger.debug(f"[MESSAGES] Mensaje {message_id} no encontrado - no procesado")
                return False
            else:
                logger.warning(f"[MESSAGES] Error verificando mensaje procesado: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"[MESSAGES] Error verificando mensaje procesado {message_id}: {e}")
            return False

    async def log_incoming_message(
        self, 
        contact_id: str, 
        message_id: str, 
        content: str, 
        flow_context: Optional[Dict] = None
    ) -> bool:
        """
        Registra un mensaje entrante.
        
        Args:
            contact_id: ID del contacto
            message_id: ID del mensaje
            content: Contenido del mensaje
            flow_context: Contexto del flujo de conversación
            
        Returns:
            bool: True si se registró exitosamente
        """
        try:
            # Asegurar contexto mínimo
            if not flow_context or (not flow_context.get("flow") and not flow_context.get("step")):
                flow_context = {"flow": "general", "step": "initial"}

            payload = {
                "contactId": contact_id,
                "messageId": message_id,
                "text": content,
                "flowContext": flow_context
            }

            logger.debug(f"[MESSAGES] Registrando mensaje entrante: {payload}")

            response = await self._make_request("POST", "message-history/log/incoming", json=payload)

            if response.status_code in [200, 201]:
                logger.info(f"[MESSAGES] Mensaje entrante registrado: {message_id}")
                return True
            elif response.status_code == 409:
                logger.debug(f"[MESSAGES] Mensaje entrante ya existía: {message_id}")
                return True  # No es error, solo ya existía
            else:
                logger.error(f"[MESSAGES] Error registrando mensaje entrante: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"[MESSAGES] Error registrando mensaje entrante {message_id}: {e}")
            return False

    async def log_outgoing_message(
        self, 
        contact_id: str, 
        message_id: str, 
        content: str, 
        flow_context: Optional[Dict] = None, 
        wa_message_id: Optional[str] = None
    ) -> bool:
        """
        Registra un mensaje saliente.
        
        Args:
            contact_id: ID del contacto
            message_id: ID del mensaje
            content: Contenido del mensaje
            flow_context: Contexto del flujo de conversación
            wa_message_id: ID del mensaje en WhatsApp
            
        Returns:
            bool: True si se registró exitosamente
        """
        try:
            # Asegurar contexto mínimo
            if not flow_context:
                flow_context = {"flow": "general", "step": "response"}

            # Asegurar que el contexto tenga los campos requeridos
            if not flow_context.get("flow"):
                flow_context["flow"] = "general"
            if not flow_context.get("step"):
                flow_context["step"] = "response"

            # Convertir contenido a texto simple si es un objeto interactivo
            text_content = self._extract_text_content(content)

            payload = {
                "contactId": contact_id,
                "messageId": message_id,
                "text": text_content,
                "flowContext": flow_context
            }

            # Agregar waMessageId si está disponible
            if wa_message_id:
                payload["waMessageId"] = wa_message_id

            logger.debug(f"[MESSAGES] Registrando mensaje saliente: {payload}")

            response = await self._make_request("POST", "message-history/log/outgoing", json=payload)

            if response.status_code in [200, 201]:
                logger.info(f"[MESSAGES] Mensaje saliente registrado: {message_id}")
                return True
            elif response.status_code == 409:
                logger.debug(f"[MESSAGES] Mensaje saliente ya existía: {message_id}")
                return True  # No es error, solo ya existía
            else:
                logger.error(f"[MESSAGES] Error registrando mensaje saliente: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"[MESSAGES] Error registrando mensaje saliente {message_id}: {e}")
            return False

    def _extract_text_content(self, content) -> str:
        """
        Extrae contenido de texto de diferentes tipos de mensaje.
        
        Args:
            content: Contenido del mensaje (string o dict)
            
        Returns:
            str: Texto extraído
        """
        if isinstance(content, str):
            return content
            
        if isinstance(content, dict):
            # Si es un mensaje interactivo, extraer el texto del body
            if content.get("type") == "interactive":
                interactive = content.get("interactive", {})
                if "body" in interactive and "text" in interactive["body"]:
                    return interactive["body"]["text"]
                else:
                    return "[Mensaje interactivo]"
            else:
                return str(content)
        
        return str(content)