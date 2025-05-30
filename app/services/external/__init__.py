"""
Módulo de clientes externos para la API de Boki.
Proporciona una interfaz unificada para mantener compatibilidad.
"""

from .base_client import BokiApiError
from .messages_api import MessagesApi
from .contacts_api import ContactsApi
from .conversations_api import ConversationsApi
from .appointments_api import AppointmentsApi

class BokiApi:
    """
    Interfaz unificada para todos los clientes de la API de Boki.
    Mantiene compatibilidad con el código existente mientras aplica SRP.
    """

    def __init__(self):
        self._messages = MessagesApi()
        self._contacts = ContactsApi()
        self._conversations = ConversationsApi()
        self._appointments = AppointmentsApi()

    # ==================== MÉTODOS DE MENSAJES ====================

    async def is_message_processed(self, message_id: str) -> bool:
        """Verifica si un mensaje ya fue procesado."""
        return await self._messages.is_message_processed(message_id)

    async def log_incoming_message(self, contact_id: str, message_id: str, content: str, flow_context=None) -> bool:
        """Registra un mensaje entrante."""
        return await self._messages.log_incoming_message(contact_id, message_id, content, flow_context)

    async def log_outgoing_message(self, contact_id: str, message_id: str, content: str, flow_context=None, wa_message_id=None) -> bool:
        """Registra un mensaje saliente."""
        return await self._messages.log_outgoing_message(contact_id, message_id, content, flow_context, wa_message_id)

    # ==================== MÉTODOS DE CONTACTOS ====================

    async def get_or_create_contact(self, phone_number: str, client_id=None):
        """Obtiene o crea un contacto."""
        return await self._contacts.get_or_create_contact(phone_number, client_id)

    async def get_contact_by_id(self, contact_id: str):
        """Obtiene un contacto por su ID."""
        return await self._contacts.get_contact_by_id(contact_id)

    async def get_client_by_phone(self, phone: str):
        """Busca un cliente por número de teléfono."""
        return await self._contacts.get_client_by_phone(phone)

    async def create_client(self, client_data):
        """Crea un nuevo cliente."""
        return await self._contacts.create_client(client_data)

    # ==================== MÉTODOS DE CONVERSACIÓN ====================

    async def get_conversation_state(self, contact_id: str):
        """Obtiene el estado actual de la conversación."""
        return await self._conversations.get_conversation_state(contact_id)

    async def save_conversation_state(self, contact_id: str, flow: str, state) -> bool:
        """Guarda el estado de conversación."""
        return await self._conversations.save_conversation_state(contact_id, flow, state)

    async def clear_conversation_state(self, contact_id: str) -> bool:
        """Elimina el estado de conversación."""
        return await self._conversations.clear_conversation_state(contact_id)

    # ==================== MÉTODOS DE CITAS ====================

    async def get_category_services(self):
        """Obtiene todas las categorías de servicios disponibles."""
        return await self._appointments.get_category_services()

    async def get_services_by_category(self, category_id: int):
        """Obtiene servicios filtrados por categoría."""
        return await self._appointments.get_services_by_category(category_id)

    async def get_professionals_by_service(self, service_id: int):
        """Obtiene profesionales asociados a un servicio."""
        return await self._appointments.get_professionals_by_service(service_id)

    async def get_general_availability(self, professional_id: int, service_id: int, days_ahead: int = 30, start_date: str = None):
        """Obtiene disponibilidad general de un profesional para un servicio."""
        return await self._appointments.get_general_availability(professional_id, service_id, days_ahead, start_date)

    async def get_available_slots(self, professional_id: int, service_id: int, date: str):
        """Obtiene slots disponibles para una fecha específica."""
        return await self._appointments.get_available_slots(professional_id, service_id, date)

    async def create_appointment(self, appointment_data):
        """Crea una nueva cita."""
        return await self._appointments.create_appointment(appointment_data)

    async def get_client_appointments(self, client_id: int, only_pending: bool = True):
        """Obtiene las citas de un cliente específico."""
        return await self._appointments.get_client_appointments(client_id, only_pending)

    # ==================== GESTIÓN DE RECURSOS ====================

    async def close(self):
        """Cierra todos los clientes HTTP."""
        await self._messages.close()
        await self._contacts.close()
        await self._conversations.close()
        await self._appointments.close()
