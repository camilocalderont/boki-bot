import httpx
from app.core.config import get_settings
import logging
from typing import Dict, Optional

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
        # Cliente HTTP reutilizable
        self.client = httpx.AsyncClient(timeout=10.0, headers=self.headers)
        
    async def is_message_processed(self, message_id: str) -> bool:
        """
        Verifica si un mensaje ya fue procesado consultando el historial
        """
        try:
            url = f"{self.base_url}/message-history/whatsapp/{message_id}"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                # El mensaje ya fue procesado
                return True
            elif response.status_code == 404:
                # El mensaje no existe, no ha sido procesado
                return False
            else:
                # Otros errores
                logger.error(f"[BOKI-API] Error verificando mensaje procesado: {response.status_code}, body: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"[BOKI-API] Excepción verificando mensaje procesado: {e}")
            return False

    async def get_or_create_contact(self, phone_number: str, client_id: Optional[int] = None) -> Dict:
        """Obtiene o crea un contacto."""
        try:
            
            # Primero intentamos obtener el contacto existente por teléfono
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.base_url}/contacts/phone/{phone_number}"
                
                response = await client.get(
                    url,
                    headers=self.headers
                )             
                
                # Si existe, lo devolvemos
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    return data
            
            # Si no existe, lo creamos
            request_data = {"phone": phone_number}
            if client_id is not None:
                request_data["clientId"] = client_id
                
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.base_url}/contacts"
                
                response = await client.post(
                    url,
                    json=request_data,
                    headers=self.headers
                )
                
                
                if response.status_code in [200, 201]:
                    data = response.json().get("data", {})
                    return data
                elif response.status_code == 409:
                    # Si hay conflicto es porque ya existe, intentamos obtenerlo nuevamente
                    return await self.get_or_create_contact(phone_number, client_id)
                else:
                    logger.error(f"[BOKI-API] Error creando contacto: {response.status_code}, body: {response.text}")
                    return {}
                
        except Exception as e:
            logger.error(f"[BOKI-API] Error en get_or_create_contact: {str(e)}")
            return {}

    async def get_conversation_state(self, contact_id: str) -> Optional[Dict]:
        """Obtiene el estado actual de la conversación."""
        try:
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.base_url}/conversation-states/contact/{contact_id}"
                
                response = await client.get(
                    url,
                    headers=self.headers
                )
                
                
                if response.status_code == 200:
                    data = response.json().get("data")
                    return data
                elif response.status_code == 404:
                    return None  # No hay estado activo
                else:
                    logger.error(f"[BOKI-API] Error obteniendo estado: {response.status_code}, body: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"[BOKI-API] Error en get_conversation_state: {str(e)}")
            return None

    async def upsert_conversation_state(self, contact_id: str, flow: str, state: Dict):
        """Crea o actualiza el estado de la conversación."""
        try:
            
            # 🔧 NUEVA ESTRATEGIA: Eliminar estado existente y crear uno nuevo
            # ya que POST está creando duplicados
            await self.clear_conversation_state(contact_id)
            
            request_data = {
                "contactId": contact_id,
                "flow": flow,
                "state": state
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Usar POST directo después de eliminar el existente
                url = f"{self.base_url}/conversation-states"
                
                response = await client.post(
                    url,
                    json=request_data,
                    headers=self.headers
                )
                
                
                if response.status_code in [200, 201]:
                    return response.json().get("data", {})
                else:
                    logger.error(f"[BOKI-API] Error creando estado: {response.status_code}, body: {response.text}")
                    return {}
                    
        except Exception as e:
            logger.error(f"[BOKI-API] Error en upsert_conversation_state: {str(e)}")
            return {}

    async def clear_conversation_state(self, contact_id: str):
        """Elimina el estado de la conversación."""
        try:
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.base_url}/conversation-states/contact/{contact_id}"
                
                response = await client.delete(
                    url,
                    headers=self.headers
                )
                
                
                if response.status_code in [200, 204]:
                    return True
                else:
                    logger.error(f"[BOKI-API] Error eliminando estado: {response.status_code}, body: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"[BOKI-API] Error en clear_conversation_state: {str(e)}")
            return False

    async def log_incoming_message(self, contact_id: str, message_id: str, content: str, flow_context: Optional[Dict]):
        """
        Registra un mensaje entrante en el historial
        """
        try:
            
            # Asegurar que flowContext tenga los campos requeridos
            if not flow_context:
                flow_context = {}
            
            # Agregar campos mínimos si no existen o son None
            if not flow_context.get('flow'):
                flow_context['flow'] = 'registration'
            if not flow_context.get('step'):
                flow_context['step'] = 'waiting_id'
            
            # Preparar datos del mensaje
            message_data = {
                "contactId": contact_id,
                "messageId": message_id,
                "content": {
                    "type": "text",
                    "text": content
                },
                "direction": "inbound",
                "flowContext": flow_context
            }
            
            
            url = f"{self.base_url}/message-history"
            
            response = await self.client.post(url, json=message_data)
            
            if response.status_code == 201:
                return True
            elif response.status_code == 409:
                return True  # ✅ No es un error, solo ya existía
            else:
                error_body = response.text
                logger.error(f"[BOKI-API] Error registrando mensaje entrante: {response.status_code}, body: {error_body}")
                return False
            
        except Exception as e:
            logger.error(f"[BOKI-API] Excepción registrando mensaje entrante: {e}")
            return False

    async def log_outgoing_message(self, contact_id: str, message_id: str, content: str, flow_context: Optional[Dict]):
        """
        Registra un mensaje saliente en el historial
        """
        try:
            
            # Asegurar que flowContext tenga los campos requeridos
            if not flow_context:
                flow_context = {}
            
            # Agregar campos mínimos si no existen o son None
            if not flow_context.get('flow'):
                flow_context['flow'] = 'registration'
            if not flow_context.get('step'):
                flow_context['step'] = 'waiting_id'
            
            # Preparar datos del mensaje
            message_data = {
                "contactId": contact_id,
                "messageId": message_id,
                "content": {
                    "type": "text",
                    "text": content
                },
                "direction": "outbound",
                "flowContext": flow_context
            }
            
            
            url = f"{self.base_url}/message-history"
            
            response = await self.client.post(url, json=message_data)
            
            if response.status_code == 201:
                return True
            elif response.status_code == 409:
                return True  # ✅ No es un error, solo ya existía
            else:
                error_body = response.text
                logger.error(f"[BOKI-API] Error registrando mensaje saliente: {response.status_code}, body: {error_body}")
                return False
            
        except Exception as e:
            logger.error(f"[BOKI-API] Excepción registrando mensaje saliente: {e}")
            return False

    async def get_client_by_phone(self, phone: str):
        """
        Busca un cliente por número de teléfono.

        Args:
            phone: Número de teléfono del cliente.

        Returns:
            dict: Datos del cliente si está registrado, None si no existe.
        """
        url = f"{self.base_url}/clients/cellphone/{phone}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code == 200:
                    # Estructura de respuesta según bokibot-api
                    return response.json().get("data")
                elif response.status_code == 404 or response.status_code == 409:
                    # Cliente no encontrado (404) o conflicto (409)
                    return None
                else:
                    logger.error(f"Error API Boki: {response.status_code} - {response.text}")
                    response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            # Solo registramos el error pero no lo propagamos si es 409
            if exc.response.status_code == 409:
                return None

            logger.error(f"Error HTTP: {exc.response.status_code} - {exc.response.text}")
            raise BokiApiError(f"Error al comunicarse con la API: {exc.response.text}") from exc
        except httpx.RequestError as exc:
            logger.error(f"Error de conexión: {str(exc)}")
            raise BokiApiError(f"Error de conexión con la API: {str(exc)}") from exc

    async def create_client(self, client_data: dict):
        """
        Crea un nuevo cliente en la base de datos.

        Args:
            client_data: Datos del cliente a crear.

        Returns:
            dict: Datos del cliente creado.
        """
        url = f"{self.base_url}/clients"
        
        try:
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    url, 
                    json=client_data,
                    headers=self.headers
                )

                
                if response.status_code in [200, 201]:
                    data = response.json().get("data")
                    return data
                else:
                    logger.error(f"[BOKI-API] Error crear cliente: {response.status_code}, body: {response.text}")
                    response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            logger.error(f"[BOKI-API] Error HTTP: {exc.response.status_code} - {exc.response.text}")
            raise BokiApiError(f"Error al comunicarse con la API: {exc.response.text}") from exc
        except httpx.RequestError as exc:
            logger.error(f"[BOKI-API] Error de conexión: {str(exc)}")
            raise BokiApiError(f"Error de conexión con la API: {str(exc)}") from exc

    # 🆕 ========================================================================
    # MÉTODOS PARA EL FLUJO DE APPOINTMENT 
    # ========================================================================

    async def get_services(self):
        """Obtiene la lista de servicios disponibles."""
        try:
            url = f"{self.base_url}/services"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                logger.error(f"[BOKI-API] Error obteniendo servicios: {response.status_code}, body: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"[BOKI-API] Error en get_services: {str(e)}")
            return []

    async def get_professionals_by_service(self, service_id: int):
        """Obtiene profesionales que ofrecen un servicio específico."""
        try:
            url = f"{self.base_url}/services/{service_id}/professionals"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                logger.error(f"[BOKI-API] Error obteniendo profesionales: {response.status_code}, body: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"[BOKI-API] Error en get_professionals_by_service: {str(e)}")
            return []

    async def get_available_dates(self, professional_id: int, service_id: int):
        """Obtiene fechas disponibles para un profesional y servicio."""
        try:
            url = f"{self.base_url}/appointments/available-dates"
            params = {
                "professionalId": professional_id,
                "serviceId": service_id
            }
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                logger.error(f"[BOKI-API] Error obteniendo fechas: {response.status_code}, body: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"[BOKI-API] Error en get_available_dates: {str(e)}")
            return []

    async def get_available_times(self, professional_id: int, date: str):
        """Obtiene horarios disponibles para un profesional en una fecha."""
        try:
            url = f"{self.base_url}/appointments/available-times"
            params = {
                "professionalId": professional_id,
                "date": date
            }
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                logger.error(f"[BOKI-API] Error obteniendo horarios: {response.status_code}, body: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"[BOKI-API] Error en get_available_times: {str(e)}")
            return []

    async def get_contact_info(self, contact_id: str):
        """Obtiene información del contacto."""
        try:
            url = f"{self.base_url}/contacts/{contact_id}"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                return response.json().get("data", {})
            else:
                logger.error(f"[BOKI-API] Error obteniendo contacto: {response.status_code}, body: {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"[BOKI-API] Error en get_contact_info: {str(e)}")
            return {}

    async def create_appointment(self, appointment_data: dict):
        """Crea una nueva cita."""
        try:
            url = f"{self.base_url}/appointments"
            response = await self.client.post(url, json=appointment_data)
            
            if response.status_code in [200, 201]:
                return response.json().get("data")
            else:
                logger.error(f"[BOKI-API] Error creando cita: {response.status_code}, body: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"[BOKI-API] Error en create_appointment: {str(e)}")
            return None

    # ========================================================================
    # MÉTODO DE LIMPIEZA
    # ========================================================================

    async def close(self):
        """Cierra el cliente HTTP"""
        if hasattr(self, 'client'):
            await self.client.aclose()