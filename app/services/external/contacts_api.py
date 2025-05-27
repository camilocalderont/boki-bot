import logging
from typing import Dict, Optional
from .base_client import BaseClient

logger = logging.getLogger(__name__)

class ContactsApi(BaseClient):
    """
    Cliente para gestión de contactos y clientes.
    Responsabilidad única: operaciones de contactos y clientes.
    """

    async def get_or_create_contact(self, phone_number: str, client_id: Optional[int] = None) -> Dict:
        """
        Obtiene o crea un contacto de forma simplificada.
        
        Args:
            phone_number: Número de teléfono del contacto
            client_id: ID del cliente asociado (opcional)
            
        Returns:
            Dict: Datos del contacto
        """
        try:
            # Intentar obtener contacto existente
            contact_data = await self._get_contact_by_phone(phone_number)
            if contact_data:
                return contact_data

            # Si no existe, crear nuevo
            return await self._create_contact(phone_number, client_id)

        except Exception as e:
            logger.error(f"[CONTACTS] Error en get_or_create_contact: {e}")
            return {}

    async def _get_contact_by_phone(self, phone_number: str) -> Optional[Dict]:
        """
        Obtiene un contacto por número de teléfono.
        
        Args:
            phone_number: Número de teléfono
            
        Returns:
            Dict: Datos del contacto o None si no existe
        """
        try:
            url = f"contacts/phone/{phone_number}"
            response = await self._make_request("GET", url)

            if response.status_code == 200:
                contact_data = response.json().get("data", {})
                logger.debug(f"[CONTACTS] Contacto encontrado: {contact_data.get('_id')}")
                return contact_data
            else:
                logger.debug(f"[CONTACTS] Contacto no encontrado para {phone_number}")
                return None

        except Exception as e:
            logger.error(f"[CONTACTS] Error obteniendo contacto: {e}")
            return None

    async def _create_contact(self, phone_number: str, client_id: Optional[int] = None) -> Dict:
        """
        Crea un nuevo contacto.
        
        Args:
            phone_number: Número de teléfono
            client_id: ID del cliente asociado (opcional)
            
        Returns:
            Dict: Datos del contacto creado
        """
        try:
            payload = {"phone": phone_number}
            if client_id:
                payload["clientId"] = client_id

            response = await self._make_request("POST", "contacts", json=payload)

            if response.status_code in [200, 201]:
                contact_data = response.json().get("data", {})
                logger.info(f"[CONTACTS] Contacto creado: {contact_data.get('_id')}")
                return contact_data
            elif response.status_code == 409:
                # Si hay conflicto, intentar obtener nuevamente
                logger.debug("[CONTACTS] Conflicto creando contacto, reintentando obtención")
                return await self._get_contact_by_phone(phone_number) or {}
            else:
                logger.error(f"[CONTACTS] Error creando contacto: {response.status_code} - {response.text}")
                return {}

        except Exception as e:
            logger.error(f"[CONTACTS] Error creando contacto: {e}")
            return {}

    async def get_client_by_phone(self, phone: str) -> Optional[Dict]:
        """
        Busca un cliente por número de teléfono.
        
        Args:
            phone: Número de teléfono
            
        Returns:
            Dict: Datos del cliente o None si no existe
        """
        try:
            url = f"clients/cellphone/{phone}"
            response = await self._make_request("GET", url)

            if response.status_code == 200:
                client_data = response.json().get("data")
                logger.debug(f"[CONTACTS] Cliente encontrado para teléfono {phone}")
                return client_data
            elif response.status_code in [404, 409]:
                logger.debug(f"[CONTACTS] Cliente no encontrado para teléfono {phone}")
                return None
            else:
                logger.warning(f"[CONTACTS] Error buscando cliente: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"[CONTACTS] Error buscando cliente por teléfono: {e}")
            return None

    async def create_client(self, client_data: Dict) -> Optional[Dict]:
        """
        Crea un nuevo cliente.
        
        Args:
            client_data: Datos del cliente a crear
            
        Returns:
            Dict: Datos del cliente creado o None si falló
        """
        try:
            response = await self._make_request("POST", "clients", json=client_data)

            if response.status_code in [200, 201]:
                created_client = response.json().get("data")
                logger.info(f"[CONTACTS] Cliente creado: {created_client.get('Id')}")
                return created_client
            else:
                logger.error(f"[CONTACTS] Error creando cliente: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"[CONTACTS] Error creando cliente: {e}")
            return None