import logging
from typing import Dict, Optional, List
from .base_client import BaseClient

logger = logging.getLogger(__name__)

class AppointmentsApi(BaseClient):
    """
    Cliente para gestión de citas, servicios y profesionales.
    Responsabilidad única: operaciones del sistema de agendamiento.
    """

    # ==================== CATEGORÍAS Y SERVICIOS ====================

    async def get_category_services(self) -> Optional[List[Dict]]:
        """
        Obtiene todas las categorías de servicios disponibles.
        
        Returns:
            List[Dict]: Lista de categorías o None si hay error
        """
        try:
            response = await self._make_request("GET", "category-services")
            
            if response.status_code == 200:
                categories = response.json().get("data", [])
                logger.debug(f"[APPOINTMENTS] Categorías obtenidas: {len(categories)} encontradas")
                return categories
            else:
                logger.error(f"[APPOINTMENTS] Error obteniendo categorías: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"[APPOINTMENTS] Error obteniendo categorías de servicios: {e}")
            return None

    async def get_services_by_category(self, category_id: int) -> Optional[List[Dict]]:
        """
        Obtiene servicios filtrados por categoría.
        
        Args:
            category_id: ID de la categoría
            
        Returns:
            List[Dict]: Lista de servicios o None si hay error
        """
        try:
            url = f"services/category/{category_id}"
            response = await self._make_request("GET", url)
            
            if response.status_code == 200:
                services = response.json().get("data", [])
                logger.debug(f"[APPOINTMENTS] Servicios por categoría {category_id}: {len(services)} encontrados")
                return services
            else:
                logger.error(f"[APPOINTMENTS] Error obteniendo servicios por categoría: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"[APPOINTMENTS] Error obteniendo servicios por categoría {category_id}: {e}")
            return None

    # ==================== PROFESIONALES ====================

    async def get_professionals_by_service(self, service_id: int) -> Optional[List[Dict]]:
        """
        Obtiene profesionales asociados a un servicio.
        
        Args:
            service_id: ID del servicio
            
        Returns:
            List[Dict]: Lista de profesionales o None si hay error
        """
        try:
            url = f"professional/service/{service_id}"
            response = await self._make_request("GET", url)
            
            if response.status_code == 200:
                professionals = response.json().get("data", [])
                logger.debug(f"[APPOINTMENTS] Profesionales por servicio {service_id}: {len(professionals)} encontrados")
                return professionals
            else:
                logger.error(f"[APPOINTMENTS] Error obteniendo profesionales: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"[APPOINTMENTS] Error obteniendo profesionales por servicio {service_id}: {e}")
            return None

    # ==================== DISPONIBILIDAD ====================

    async def get_general_availability(self, professional_id: int, service_id: int, days_ahead: int = 30, start_date: str = None) -> Optional[List[Dict]]:
        """
        Obtiene disponibilidad general de un profesional para un servicio.
        
        Args:
            professional_id: ID del profesional
            service_id: ID del servicio
            days_ahead: Días hacia adelante a consultar
            start_date: Fecha de inicio en formato MM/DD/YYYY (opcional)
            
        Returns:
            List[Dict]: Lista de fechas disponibles o None si hay error
        """
        try:
            url = f"professional/{professional_id}/general-availability"
            params = {
                "serviceId": service_id,
                "daysAhead": days_ahead
            }
            
            # Agregar startDate si se proporciona
            if start_date:
                params["startDate"] = start_date
                
            response = await self._make_request("GET", url, params=params)
            
            if response.status_code == 200:
                availability = response.json().get("data", [])
                logger.debug(f"[APPOINTMENTS] Disponibilidad general obtenida: {len(availability)} fechas")
                return availability
            else:
                logger.error(f"[APPOINTMENTS] Error obteniendo disponibilidad general: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"[APPOINTMENTS] Error obteniendo disponibilidad general: {e}")
            return None

    async def get_available_slots(self, professional_id: int, service_id: int, date: str) -> Optional[Dict]:
        """
        Obtiene slots disponibles para una fecha específica.
        
        Args:
            professional_id: ID del profesional
            service_id: ID del servicio
            date: Fecha en formato ISO (2025-05-27)
            
        Returns:
            Dict: Diccionario con slots organizados por período o None si hay error
            Estructura: {"mañana": [...], "tarde": [...], "noche": [...]}
        """
        try:
            url = f"professional/{professional_id}/available-slots"
            params = {
                "serviceId": service_id,
                "date": date
            }
            response = await self._make_request("GET", url, params=params)
            
            if response.status_code == 200:
                response_data = response.json()
                slots_data = response_data.get("data", {})
                
                # Contar total de slots disponibles para logging
                total_slots = 0
                for period in ["mañana", "tarde", "noche"]:
                    period_slots = slots_data.get(period, [])
                    total_slots += len(period_slots)
                
                logger.debug(f"[APPOINTMENTS] Slots disponibles para {date}: {total_slots} encontrados")
                logger.debug(f"[APPOINTMENTS] Distribución: mañana={len(slots_data.get('mañana', []))}, tarde={len(slots_data.get('tarde', []))}, noche={len(slots_data.get('noche', []))}")
                
                return slots_data
            else:
                logger.error(f"[APPOINTMENTS] Error obteniendo slots disponibles: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"[APPOINTMENTS] Error obteniendo slots disponibles: {e}")
            return None

    # ==================== CITAS ====================

    async def create_appointment(self, appointment_data: Dict) -> Optional[Dict]:
        """
        Crea una nueva cita.
        
        Args:
            appointment_data: Datos de la cita a crear
            
        Returns:
            Dict: Datos de la cita creada o None si hay error
        """
        try:
            response = await self._make_request("POST", "appointments", json=appointment_data)
            
            if response.status_code in [200, 201]:
                appointment = response.json().get("data")
                logger.info(f"[APPOINTMENTS] Cita creada exitosamente: {appointment.get('id')}")
                return appointment
            else:
                logger.error(f"[APPOINTMENTS] Error creando cita: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"[APPOINTMENTS] Error creando cita: {e}")
            return None

    async def get_client_appointments(self, client_id: int, only_pending: bool = True) -> Optional[List[Dict]]:
        """
        Obtiene las citas de un cliente específico.
        
        Args:
            client_id: ID del cliente
            only_pending: Si solo mostrar citas pendientes (por defecto True)
            
        Returns:
            List[Dict]: Lista de citas del cliente o None si hay error
        """
        try:
            url = f"appointments/client/{client_id}"
            params = {}
            if only_pending:
                params["status"] = "pending"
                
            response = await self._make_request("GET", url, params=params)
            
            if response.status_code == 200:
                appointments = response.json().get("data", [])
                logger.debug(f"[APPOINTMENTS] Citas obtenidas para cliente {client_id}: {len(appointments)} encontradas")
                return appointments
            else:
                logger.error(f"[APPOINTMENTS] Error obteniendo citas del cliente: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"[APPOINTMENTS] Error obteniendo citas del cliente {client_id}: {e}")
            return None