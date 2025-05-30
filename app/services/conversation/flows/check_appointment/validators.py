import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class CheckAppointmentValidators:
    """
    Responsabilidad única: Validaciones específicas del flujo de consulta de citas.
    """

    @staticmethod
    def validate_appointments(appointments: List[Dict]) -> bool:
        """Valida que la lista de citas sea válida."""
        return bool(appointments) and len(appointments) > 0

    @staticmethod
    def validate_client_data(client_data: Dict) -> bool:
        """Valida que los datos del cliente sean válidos."""
        return bool(client_data) and client_data.get('Id') is not None

    @staticmethod
    def validate_contact_info(contact_info: Dict) -> bool:
        """Valida que la información del contacto sea válida."""
        return bool(contact_info) and contact_info.get('phone') is not None 