# app/services/boki_api.py
import httpx
import logging
import uuid
from typing import Dict, Optional, Any
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class BokiApiError(Exception):
    """Error al llamar a la API de Boki."""
    pass

class BokiApi:
    """
    Cliente para comunicarse con la API de Boki (bokibot-api).
    Responsabilidad única: comunicación con el backend.
    """

    def __init__(self):
        if settings.API_PORT:
            self.base_url = f"{settings.API_URL}:{settings.API_PORT}/api/v{settings.API_VERSION}"
        else:
            self.base_url = f"{settings.API_URL}/api/v{settings.API_VERSION}"
        
        self.headers = {
            "Content-Type": "application/json",
            "x-api-token": settings.API_TOKEN
        }
        
        # Cliente HTTP reutilizable con configuración optimizada
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers=self.headers,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

    async def _make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Método centralizado para hacer requests con manejo de errores."""
        try:
            full_url = url if url.startswith('http') else f"{self.base_url}/{url.lstrip('/')}"
            logger.debug(f"[API] {method} {full_url}")
            
            response = await self.client.request(method, full_url, **kwargs)
            logger.debug(f"[API] {method} {full_url} -> {response.status_code}")
            
            if response.status_code >= 400:
                logger.error(f"[API] Error {response.status_code}: {response.text}")
            
            return response
        except httpx.TimeoutException:
            logger.error(f"[API] Timeout en {method} {url}")
            raise BokiApiError(f"Timeout al comunicarse con la API")
        except httpx.RequestError as e:
            logger.error(f"[API] Error de conexión en {method} {url}: {e}")
            raise BokiApiError(f"Error de conexión: {str(e)}")

    # ==================== MANEJO DE MENSAJES ====================

    async def is_message_processed(self, message_id: str) -> bool:
        """Verifica si un mensaje ya fue procesado."""
        try:
            # Usar el endpoint correcto: GET /message-history/whatsapp/{messageId}
            url = f"message-history/whatsapp/{message_id}"
            response = await self._make_request("GET", url)
            
            if response.status_code == 200:
                result = response.json().get("data")
                is_processed = result is not None
                logger.debug(f"[API] Mensaje {message_id} procesado: {is_processed}")
                return is_processed
            elif response.status_code == 404:
                logger.debug(f"[API] Mensaje {message_id} no encontrado - no procesado")
                return False
            else:
                logger.warning(f"[API] Error verificando mensaje procesado: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"[API] Error verificando mensaje procesado {message_id}: {e}")
            return False

    async def log_incoming_message(self, contact_id: str, message_id: str, content: str, flow_context: Optional[Dict] = None) -> bool:
        """Registra un mensaje entrante."""
        try:
            # Asegurar contexto mínimo
            if not flow_context:
                flow_context = {"flow": "general", "step": "initial"}
            
            # Asegurar que el contexto tenga los campos requeridos
            if not flow_context.get("flow"):
                flow_context["flow"] = "general"
            if not flow_context.get("step"):
                flow_context["step"] = "initial"

            # Usar la estructura correcta del endpoint POST /message-history
            payload = {
                "contactId": contact_id,
                "messageId": message_id,
                "direction": "inbound",  # Requerido
                "content": {
                    "type": "text",
                    "text": content
                },
                "flowContext": flow_context
            }
            
            logger.debug(f"[API] Registrando mensaje entrante: {payload}")
            
            url = "message-history"
            response = await self._make_request("POST", url, json=payload)
            
            if response.status_code in [200, 201]:
                logger.info(f"[API] Mensaje entrante registrado: {message_id}")
                return True
            elif response.status_code == 409:
                logger.debug(f"[API] Mensaje entrante ya existía: {message_id}")
                return True  # No es error, solo ya existía
            else:
                logger.error(f"[API] Error registrando mensaje entrante: {response.status_code} - {response.text}")
                return False
            
        except Exception as e:
            logger.error(f"[API] Error registrando mensaje entrante {message_id}: {e}")
            return False

    async def log_outgoing_message(self, contact_id: str, message_id: str, content: str, flow_context: Optional[Dict] = None, wa_message_id: Optional[str] = None) -> bool:
        """Registra un mensaje saliente."""
        try:
            # Asegurar contexto mínimo
            if not flow_context:
                flow_context = {"flow": "general", "step": "response"}
            
            # Asegurar que el contexto tenga los campos requeridos
            if not flow_context.get("flow"):
                flow_context["flow"] = "general"
            if not flow_context.get("step"):
                flow_context["step"] = "response"

            # Usar la estructura correcta del endpoint POST /message-history
            payload = {
                "contactId": contact_id,
                "messageId": message_id,
                "direction": "outbound",  # Requerido
                "content": {
                    "type": "text",
                    "text": content
                },
                "flowContext": flow_context
            }
            
            # Agregar waMessageId si está disponible
            if wa_message_id:
                payload["waMessageId"] = wa_message_id
            
            logger.debug(f"[API] Registrando mensaje saliente: {payload}")
            
            url = "message-history"
            response = await self._make_request("POST", url, json=payload)
            
            if response.status_code in [200, 201]:
                logger.info(f"[API] Mensaje saliente registrado: {message_id}")
                return True
            elif response.status_code == 409:
                logger.debug(f"[API] Mensaje saliente ya existía: {message_id}")
                return True  # No es error, solo ya existía
            else:
                logger.error(f"[API] Error registrando mensaje saliente: {response.status_code} - {response.text}")
                return False
            
        except Exception as e:
            logger.error(f"[API] Error registrando mensaje saliente {message_id}: {e}")
            return False

    # ==================== GESTIÓN DE CONTACTOS ====================

    async def get_or_create_contact(self, phone_number: str, client_id: Optional[int] = None) -> Dict:
        """Obtiene o crea un contacto de forma simplificada."""
        try:
            # Intentar obtener contacto existente
            url = f"contacts/phone/{phone_number}"
            response = await self._make_request("GET", url)
            
            if response.status_code == 200:
                contact_data = response.json().get("data", {})
                logger.debug(f"[API] Contacto encontrado: {contact_data.get('_id')}")
                return contact_data
            
            # Si no existe, crear nuevo
            payload = {"phone": phone_number}
            if client_id:
                payload["clientId"] = client_id
                
            url = "contacts"
            response = await self._make_request("POST", url, json=payload)
            
            if response.status_code in [200, 201]:
                contact_data = response.json().get("data", {})
                logger.info(f"[API] Contacto creado: {contact_data.get('_id')}")
                return contact_data
            elif response.status_code == 409:
                # Si hay conflicto, intentar obtener nuevamente (una sola vez)
                logger.debug("[API] Conflicto creando contacto, reintentando obtención")
                url = f"contacts/phone/{phone_number}"
                response = await self._make_request("GET", url)
                if response.status_code == 200:
                    return response.json().get("data", {})
                else:
                    logger.error(f"[API] No se pudo obtener contacto después de conflicto")
                    return {}
            else:
                logger.error(f"[API] Error creando contacto: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"[API] Error en get_or_create_contact: {e}")
            return {}

    # ==================== GESTIÓN DE ESTADOS DE CONVERSACIÓN ====================

    async def get_conversation_state(self, contact_id: str) -> Optional[Dict]:
        """Obtiene el estado actual de la conversación."""
        try:
            url = f"conversation-states/contact/{contact_id}"
            response = await self._make_request("GET", url)
            
            if response.status_code == 200:
                state_data = response.json().get("data")
                logger.debug(f"[API] Estado obtenido para contacto {contact_id}: {state_data}")
                return state_data
            elif response.status_code == 404:
                logger.debug(f"[API] No hay estado activo para contacto {contact_id}")
                return None
            else:
                logger.warning(f"[API] Error obteniendo estado: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"[API] Error obteniendo estado de conversación: {e}")
            return None

    async def save_conversation_state(self, contact_id: str, flow: str, state: Dict) -> bool:
        """Guarda el estado de conversación de forma simplificada."""
        try:
            # Primero limpiar estado existente
            await self.clear_conversation_state(contact_id)
            
            payload = {
                "contactId": contact_id,
                "flow": flow,
                "state": state
            }
            
            logger.debug(f"[API] Guardando estado: {payload}")
            
            url = "conversation-states"
            response = await self._make_request("POST", url, json=payload)
            
            if response.status_code in [200, 201]:
                logger.debug(f"[API] Estado guardado para contacto {contact_id} en flujo {flow}")
                return True
            else:
                logger.error(f"[API] Error guardando estado: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"[API] Error guardando estado de conversación: {e}")
            return False

    async def clear_conversation_state(self, contact_id: str) -> bool:
        """Elimina el estado de conversación."""
        try:
            url = f"conversation-states/contact/{contact_id}"
            response = await self._make_request("DELETE", url)
            
            if response.status_code in [200, 204, 404]:  # 404 es OK, ya no existe
                logger.debug(f"[API] Estado eliminado para contacto {contact_id}")
                return True
            else:
                logger.warning(f"[API] Error eliminando estado: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"[API] Error eliminando estado: {e}")
            return False

    # ==================== GESTIÓN DE CLIENTES ====================

    async def get_client_by_phone(self, phone: str) -> Optional[Dict]:
        """Busca un cliente por número de teléfono."""
        try:
            url = f"clients/cellphone/{phone}"
            response = await self._make_request("GET", url)
            
            if response.status_code == 200:
                client_data = response.json().get("data")
                logger.debug(f"[API] Cliente encontrado para teléfono {phone}")
                return client_data
            elif response.status_code in [404, 409]:
                logger.debug(f"[API] Cliente no encontrado para teléfono {phone}")
                return None
            else:
                logger.warning(f"[API] Error buscando cliente: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"[API] Error buscando cliente por teléfono: {e}")
            return None

    async def create_client(self, client_data: Dict) -> Optional[Dict]:
        """Crea un nuevo cliente."""
        try:
            url = "clients"
            response = await self._make_request("POST", url, json=client_data)
            
            if response.status_code in [200, 201]:
                created_client = response.json().get("data")
                logger.info(f"[API] Cliente creado: {created_client.get('Id')}")
                return created_client
            else:
                logger.error(f"[API] Error creando cliente: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"[API] Error creando cliente: {e}")
            return None

    # ==================== GESTIÓN DE RECURSOS ====================

    async def close(self):
        """Cierra el cliente HTTP."""
        try:
            await self.client.aclose()
            logger.debug("[API] Cliente HTTP cerrado")
        except Exception as e:
            logger.error(f"[API] Error cerrando cliente: {e}")