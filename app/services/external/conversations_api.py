import logging
from typing import Dict, Optional
from .base_client import BaseClient

logger = logging.getLogger(__name__)

class ConversationsApi(BaseClient):
    """
    Cliente para gestión de estados de conversación.
    Responsabilidad única: operaciones de estados de conversación.
    """

    async def get_conversation_state(self, contact_id: str) -> Optional[Dict]:
        """
        Obtiene el estado actual de la conversación.
        
        Args:
            contact_id: ID del contacto
            
        Returns:
            Dict: Estado de la conversación o None si no existe
        """
        try:
            url = f"conversation-states/contact/{contact_id}"
            response = await self._make_request("GET", url)

            if response.status_code == 200:
                state_data = response.json().get("data")
                logger.debug(f"[CONVERSATIONS] Estado obtenido para contacto {contact_id}: {state_data}")
                return state_data
            elif response.status_code == 404:
                logger.debug(f"[CONVERSATIONS] No hay estado activo para contacto {contact_id}")
                return None
            else:
                logger.warning(f"[CONVERSATIONS] Error obteniendo estado: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"[CONVERSATIONS] Error obteniendo estado de conversación: {e}")
            return None

    async def save_conversation_state(self, contact_id: str, flow: str, state: Dict) -> bool:
        """
        Guarda el estado de conversación.
        
        Args:
            contact_id: ID del contacto
            flow: Nombre del flujo
            state: Estado a guardar
            
        Returns:
            bool: True si se guardó exitosamente
        """
        try:
            payload = {
                "contactId": contact_id,
                "flow": flow,
                "step": state.get("step"),
                "data": state.get("data"),
            }

            logger.debug(f"[CONVERSATIONS] Guardando estado: {payload}")

            response = await self._make_request("POST", "conversation-states", json=payload)

            if response.status_code in [200, 201]:
                logger.debug(f"[CONVERSATIONS] Estado guardado para contacto {contact_id} en flujo {flow}")
                return True
            else:
                logger.error(f"[CONVERSATIONS] Error guardando estado: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"[CONVERSATIONS] Error guardando estado de conversación: {e}")
            return False

    async def clear_conversation_state(self, contact_id: str) -> bool:
        """
        Elimina el estado de conversación.
        
        Args:
            contact_id: ID del contacto
            
        Returns:
            bool: True si se eliminó exitosamente
        """
        try:
            url = f"conversation-states/contact/{contact_id}"
            response = await self._make_request("DELETE", url)

            if response.status_code in [200, 204, 404]:  # 404 es OK, ya no existe
                logger.debug(f"[CONVERSATIONS] Estado eliminado para contacto {contact_id}")
                return True
            else:
                logger.warning(f"[CONVERSATIONS] Error eliminando estado: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"[CONVERSATIONS] Error eliminando estado: {e}")
            return False