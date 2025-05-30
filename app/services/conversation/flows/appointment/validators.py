# ================================
# 3. flows/appointment/validators.py
# ================================
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class AppointmentValidators:
    """
    Responsabilidad única: Validaciones específicas del flujo de appointment.
    """

    @staticmethod
    def validate_categories(categories: List[Dict]) -> bool:
        """Valida que las categorías sean válidas para servicios."""
        if not categories:
            return False
        
        # Filtrar solo categorías de servicios
        service_categories = [
            cat for cat in categories 
            if cat.get('BIsService', True)
        ]
        
        return len(service_categories) > 0

    @staticmethod
    def validate_services(services: List[Dict]) -> bool:
        """Valida que los servicios sean válidos."""
        return bool(services)

    @staticmethod
    def validate_professionals(professionals: List[Dict]) -> bool:
        """Valida que los profesionales sean válidos."""
        return bool(professionals)

    @staticmethod
    def validate_availability(availability: List[Dict]) -> bool:
        """Valida que haya disponibilidad."""
        return bool(availability)
    
    @staticmethod
    def validate_slots_data(slots_data: Optional[Dict]) -> bool:
        """
        Valida que los datos de slots tengan la estructura correcta y contengan al menos un horario.
        
        Args:
            slots_data: Diccionario con estructura {"mañana": [...], "tarde": [...], "noche": [...]}
            
        Returns:
            bool: True si la estructura es válida y hay al menos un horario disponible
        """
        if not slots_data or not isinstance(slots_data, dict):
            return False
        
        # Verificar que al menos un período tenga horarios
        periods = ["mañana", "tarde", "noche"]
        for period in periods:
            period_slots = slots_data.get(period, [])
            if period_slots and len(period_slots) > 0:
                return True
        
        return False

    @staticmethod
    def validate_slots(slots):
        """Mantener compatibilidad con validador anterior si es necesario."""
        if isinstance(slots, dict):
            # Nueva estructura de períodos
            return AppointmentValidators.validate_slots_data(slots)
        else:
            # Estructura anterior (lista directa)
            return slots is not None and len(slots) > 0

    @staticmethod
    def validate_appointment_data(data: Dict) -> tuple[bool, List[str]]:
        """Valida que todos los datos necesarios para crear una cita estén presentes."""
        required_fields = {
            "professional": data.get("selected_professional"),
            "service": data.get("selected_service"),
            "date": data.get("selected_date"),
            "slot": data.get("selected_slot")
        }
        
        missing_fields = []
        for field_name, value in required_fields.items():
            if not value:
                missing_fields.append(field_name)
        
        # Validar IDs específicos
        if required_fields["professional"] and not required_fields["professional"].get('Id'):
            missing_fields.append("professional_id")
        if required_fields["service"] and not required_fields["service"].get('Id'):
            missing_fields.append("service_id")
        if required_fields["slot"] and not required_fields["slot"].get('start_time'):
            missing_fields.append("start_time")
        
        return len(missing_fields) == 0, missing_fields