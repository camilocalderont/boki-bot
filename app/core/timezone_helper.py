import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

# Timezone de Colombia (UTC-5)
COLOMBIA_TZ = pytz.timezone('America/Bogota')

class TimezoneHelper:
    """
    Helper para manejar fechas en formato ISO (2025-05-27) para Colombia.
    Responsabilidad única: conversiones de fecha ISO a formatos legibles.
    """
    
    @staticmethod
    def get_colombia_now() -> datetime:
        """Obtiene la fecha y hora actual en timezone de Colombia."""
        return datetime.now(COLOMBIA_TZ)
    
    @staticmethod
    def get_weekday_name_spanish(weekday: int) -> str:
        """
        Convierte número de día a nombre en español.
        
        Args:
            weekday: Número del día (1=Lunes, 7=Domingo)
            
        Returns:
            str: Nombre del día en español
        """
        days = {
            1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 
            5: "Viernes", 6: "Sábado", 7: "Domingo"
        }
        return days.get(weekday, "Desconocido")
    
    @staticmethod
    def format_date_for_whatsapp(iso_date: str) -> str:
        """
        Convierte fecha ISO a formato para WhatsApp.
        
        Args:
            iso_date: Fecha en formato ISO "2025-05-27"
                        
        Returns:
            str: Fecha formateada para WhatsApp "27/05 - Mar"
        """
        try:
            # Parsear fecha ISO
            dt = datetime.strptime(iso_date, "%Y-%m-%d")
            
            # Localizar a Colombia
            dt = COLOMBIA_TZ.localize(dt)
            
            # Formatear: "27/05 - Mar"
            formatted_date = dt.strftime('%d/%m')
            weekday_name = TimezoneHelper.get_weekday_name_spanish(dt.weekday())
            
            return f"{formatted_date} - {weekday_name[:3]}"
            
        except Exception as e:
            return iso_date  # Fallback: devolver original
    
    @staticmethod
    def format_date_for_confirmation(iso_date: str) -> str:
        """
        Formatea fecha ISO para mostrar en confirmación de cita.
        
        Args:
            iso_date: Fecha en formato ISO "2025-05-27"
            
        Returns:
            str: Fecha formateada "27/05/2025 - Martes"
        """
        try:
            # Parsear fecha ISO
            dt = datetime.strptime(iso_date, "%Y-%m-%d")
            
            # Localizar a Colombia
            dt = COLOMBIA_TZ.localize(dt)
            
            # Formatear: "27/05/2025 - Martes"
            weekday_name = TimezoneHelper.get_weekday_name_spanish(dt.weekday())
            return f"{dt.strftime('%d/%m/%Y')} - {weekday_name}"
            
        except Exception as e:
            return iso_date
    
    @staticmethod
    def is_date_today(iso_date: str) -> bool:
        """
        Verifica si una fecha ISO es hoy en timezone colombiano.
        
        Args:
            iso_date: Fecha en formato ISO "2025-05-27"
            
        Returns:
            bool: True si es hoy
        """
        try:
            dt = datetime.strptime(iso_date, "%Y-%m-%d")
            dt = COLOMBIA_TZ.localize(dt)
            
            # Comparar solo fechas (sin hora)
            today = TimezoneHelper.get_colombia_now().date()
            return dt.date() == today
            
        except Exception as e:
            return False
    
    @staticmethod
    def is_date_tomorrow(iso_date: str) -> bool:
        """
        Verifica si una fecha ISO es mañana en timezone colombiano.
        
        Args:
            iso_date: Fecha en formato ISO "2025-05-27"
            
        Returns:
            bool: True si es mañana
        """
        try:
            dt = datetime.strptime(iso_date, "%Y-%m-%d")
            dt = COLOMBIA_TZ.localize(dt)
            
            # Comparar con mañana
            colombia_now = TimezoneHelper.get_colombia_now()
            tomorrow = colombia_now.replace(day=colombia_now.day + 1).date()
            return dt.date() == tomorrow
            
        except Exception as e:
            return False

# ============================================================================
# FUNCIONES DE CONVENIENCIA
# ============================================================================

def format_date_for_whatsapp(iso_date: str) -> str:
    """
    Función de conveniencia para formatear fechas ISO para WhatsApp.
    
    Args:
        iso_date: Fecha en formato "2025-05-27"
        
    Returns:
        str: Fecha formateada "27/05 - Mar"
    """
    return TimezoneHelper.format_date_for_whatsapp(iso_date)

def format_date_for_confirmation(iso_date: str) -> str:
    """
    Función de conveniencia para formatear fechas ISO de confirmación.
    
    Args:
        iso_date: Fecha en formato "2025-05-27"
        
    Returns:
        str: Fecha formateada "27/05/2025 - Martes"
    """
    return TimezoneHelper.format_date_for_confirmation(iso_date)
