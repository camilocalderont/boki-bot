# ================================
# 2. flows/appointment/data_formatter.py
# ================================
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DataFormatter:
    """
    Responsabilidad única: Formatear datos para mostrar al usuario.
    """

    @staticmethod
    def format_professional_name(professional: Dict) -> str:
        """Formatea el nombre completo del profesional."""
        first_name = professional.get('VcFirstName', '') or ''
        second_name = professional.get('VcSecondName', '') or ''
        first_lastname = professional.get('VcFirstLastName', '') or ''
        second_lastname = professional.get('VcSecondLastName', '') or ''
        
        first_name = first_name.strip()
        second_name = second_name.strip()
        first_lastname = first_lastname.strip()
        second_lastname = second_lastname.strip()
        
        name_parts = [first_name]
        if second_name:
            name_parts.append(second_name)
        if first_lastname:
            name_parts.append(first_lastname)
        if second_lastname:
            name_parts.append(second_lastname)
        
        return ' '.join(name_parts)

    @staticmethod
    def format_professional_display_name(professional: Dict, max_length: int = 20) -> str:
        """Formatea nombre del profesional para listas (máximo 20 caracteres)."""
        first_name = professional.get('VcFirstName', '') or ''
        last_name = professional.get('VcFirstLastName', '') or ''
        
        first_name = first_name.strip()
        last_name = last_name.strip()
        
        if last_name:
            full_name = f"{first_name} {last_name}"
            if len(full_name) <= max_length:
                return full_name
            else:
                return f"{first_name} {last_name[0]}."[:max_length]
        
        return first_name[:max_length]

    @staticmethod
    def format_professional_detailed_info(professional: Dict) -> str:
        """Formatea información detallada del profesional."""
        name = DataFormatter.format_professional_name(professional)
        specialization = professional.get('VcSpecialization', '')
        profession = professional.get('VcProfession', '')
        years_exp = professional.get('IYearsOfExperience', 0)
        
        info = f"👨‍⚕️ *{name}*"
        
        # Profesión y especialización
        if specialization and profession:
            if specialization.lower() != profession.lower():
                info += f"\n   📋 {profession} - Especialista en {specialization}"
            else:
                info += f"\n   📋 Especialista en {specialization}"
        elif specialization:
            info += f"\n   📋 Especialista en {specialization}"
        elif profession:
            info += f"\n   📋 {profession}"
        
        # Experiencia
        if years_exp > 0:
            info += f"\n   🎯 {years_exp} años de experiencia"
        
        return info

    @staticmethod
    def format_date_display(date_str: str) -> str:
        """Formatea fecha para mostrar al usuario."""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d/%m - %a')
            
            # Traducir días de la semana
            day_translations = {
                'Mon': 'Lun', 'Tue': 'Mar', 'Wed': 'Mié', 
                'Thu': 'Jue', 'Fri': 'Vie', 'Sat': 'Sáb', 'Sun': 'Dom'
            }
            for eng, esp in day_translations.items():
                formatted_date = formatted_date.replace(eng, esp)
            
            return formatted_date
        except:
            return date_str

    @staticmethod
    def format_full_date_display(date_str: str) -> str:
        """Formatea fecha completa para confirmación."""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d/%m/%Y - %A')
            
            # Traducir día de la semana
            day_translations = {
                'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
                'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            }
            for eng, esp in day_translations.items():
                formatted_date = formatted_date.replace(eng, esp)
            
            return formatted_date
        except:
            return date_str

    @staticmethod
    def clean_data_for_storage(data: Any) -> Any:
        """Limpia datos pesados para almacenamiento (quita imágenes)."""
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                # Omitir campos de imágenes pesados
                if key in ['TxPicture', 'TxPhoto', 'TxLogo', 'TxImages']:
                    continue
                elif isinstance(value, (dict, list)):
                    cleaned[key] = DataFormatter.clean_data_for_storage(value)
                else:
                    cleaned[key] = value
            return cleaned
        elif isinstance(data, list):
            return [DataFormatter.clean_data_for_storage(item) for item in data]
        else:
            return data
        
    @staticmethod
    def format_backend_date_for_display_simple(date_info: Dict) -> str:
        """
        Versión simplificada que usa directamente el campo 'fecha' del backend.
        
        Args:
            date_info: Objeto del backend con 'fecha'
            
        Returns:
            str: Fecha formateada usando directamente los datos del backend
        """
        try:
            # Usar directamente el campo 'fecha' que ya viene bien formateado
            fecha_amigable = date_info.get('fecha', '')
            
            if fecha_amigable:
                # "Martes 27 de mayo" -> "Mar 27 May"
                # Simplificar directamente sin crear nuevas fechas
                return fecha_amigable.replace(' de ', ' ')  # "Martes 27 mayo"
            
            # Fallback
            fecha_completa = date_info.get('fechaCompleta', '')
            if fecha_completa:
                fecha_parte = fecha_completa.split()[0]  # "27/05/2025"
                return fecha_parte  # Mostrar "27/05/2025"
                
            return "Fecha disponible"
            
        except Exception as e:
            logger.warning(f"Error formateando fecha simple: {e}")
            return "Fecha disponible"
            

    @staticmethod
    def format_availability_description(date_info: Dict) -> str:
        """
        Crea una descripción amigable para la disponibilidad.
        
        Args:
            date_info: Objeto del backend con horarios
            
        Returns:
            str: Descripción amigable
        """
        try:
            hora_inicio = date_info.get('horaInicio', '')
            hora_fin = date_info.get('horaFin', '')
            descanso_inicio = date_info.get('descansoInicio')
            descanso_fin = date_info.get('descansoFin')
            
            if hora_inicio and hora_fin:
                # Formato básico: "8:00 - 17:00"
                descripcion = f"{hora_inicio} - {hora_fin}"
                
                # Agregar información del descanso si existe
                if descanso_inicio and descanso_fin:
                    descripcion += f" (pausa {descanso_inicio}-{descanso_fin})"
                
                return descripcion
            else:
                return "Disponible para reservar"
                
        except Exception as e:
            logger.warning(f"Error formateando descripción de disponibilidad: {e}")
            return "Disponible para reservar"

    @staticmethod
    def convert_date_for_api(date_info: Dict) -> str:
        """
        Convierte fecha del backend al formato YYYY-MM-DD para la API.
        
        Args:
            date_info: Objeto del backend con 'fechaCompleta'
            
        Returns:
            str: Fecha en formato YYYY-MM-DD o None si hay error
        """
        try:
            fecha_completa = date_info.get('fechaCompleta', '')
            if fecha_completa:
                # "27/05/2025 00:00" -> "2025-05-27"
                fecha_parte = fecha_completa.split()[0]  # "27/05/2025"
                dia, mes, año = fecha_parte.split('/')
                return f"{año}-{mes}-{dia}"  # ✅ CAMBIADO: formato YYYY-MM-DD
            return None
        except Exception as e:
            logger.warning(f"Error convirtiendo fecha para API: {e}")
            return None
        
    @staticmethod
    def format_stored_date_for_confirmation(date_string: str, time_string: str = None) -> Dict[str, str]:
        """
        Formatea fecha y hora almacenadas para mostrar en confirmación de cita.
        Resuelve problemas de timezone y formato 12h/24h.
        
        Args:
            date_string: Fecha en formato "2025-05-28" o "28/05/2025" o "28/05/2025 19:00"
            time_string: Hora opcional en formato "1:00 PM" o "13:00"
        
        Returns:
            Dict con fecha y hora formateadas correctamente
        """
        import pytz
        from datetime import datetime
        
        try:
            logger.info(f"[DEBUG] Formateando para confirmación: fecha='{date_string}', hora='{time_string}'")
            
            # Zona horaria (cambiar según tu ubicación)
            local_tz = pytz.timezone('America/Bogota')
            
            # Parsear la fecha según el formato
            if '/' in date_string and ' ' in date_string:
                # Formato "28/05/2025 19:00" - extraer fecha y hora
                date_part, time_part = date_string.split(' ', 1)
                dt = datetime.strptime(date_part, "%d/%m/%Y")
                if not time_string:
                    time_string = time_part
            elif '/' in date_string:
                # Formato "28/05/2025"
                dt = datetime.strptime(date_string, "%d/%m/%Y")
            elif '-' in date_string:
                # Formato "2025-05-28"
                dt = datetime.strptime(date_string, "%Y-%m-%d")
            else:
                raise ValueError(f"Formato de fecha no reconocido: {date_string}")
            
            # Asignar zona horaria
            dt = local_tz.localize(dt)
            
            # Mapeo de días y meses en español
            days_es = {
                'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
                'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            }
            
            months_es = {
                'January': 'enero', 'February': 'febrero', 'March': 'marzo',
                'April': 'abril', 'May': 'mayo', 'June': 'junio',
                'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
                'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
            }
            
            # Formatear fecha
            day_name_en = dt.strftime("%A")
            month_name_en = dt.strftime("%B")
            
            day_name = days_es.get(day_name_en, day_name_en)
            month_name = months_es.get(month_name_en, month_name_en)
            
            fecha_completa = f"{day_name} {dt.day} de {month_name}"
            
            # Formatear hora si se proporciona
            hora_12 = ""
            if time_string:
                hora_12 = DataFormatter._convert_time_to_12h(time_string)
            
            result = {
                "fecha_completa": fecha_completa,
                "hora_12": hora_12,
                "fecha_iso": dt.date().isoformat(),
                "timestamp": int(dt.timestamp())
            }
            
            logger.info(f"[DEBUG] Resultado formateado: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error formateando fecha/hora '{date_string}'/'{time_string}': {e}")
            return {
                "fecha_completa": "Fecha seleccionada",
                "hora_12": time_string or "Hora seleccionada",
                "fecha_iso": date_string,
                "timestamp": 0
            }

    @staticmethod
    def _convert_time_to_12h(time_string: str) -> str:
        """
        Convierte hora a formato 12h con AM/PM.
        
        Args:
            time_string: Hora en formato "13:00", "1:00 PM", "19:00", etc.
        
        Returns:
            str: Hora en formato "1:00 PM"
        """
        try:
            from datetime import datetime
            
            # Si ya tiene AM/PM, devolverlo como está
            if 'AM' in time_string.upper() or 'PM' in time_string.upper():
                return time_string
            
            # Si es formato 24h (HH:MM)
            if ':' in time_string and len(time_string.split(':')) == 2:
                time_obj = datetime.strptime(time_string, "%H:%M")
                return time_obj.strftime("%I:%M %p")
            
            # Fallback
            return time_string
            
        except Exception as e:
            logger.warning(f"Error convirtiendo hora '{time_string}': {e}")
            return time_string

    @staticmethod
    def debug_date_formatting(date_string: str, time_string: str = None) -> Dict:
        """Función de debugging para verificar formateo de fechas"""
        try:
            result = DataFormatter.format_stored_date_for_confirmation(date_string, time_string)
            return {
                "input_date": date_string,
                "input_time": time_string,
                "output": result,
                "success": True
            }
        except Exception as e:
            return {
                "input_date": date_string,
                "input_time": time_string,
                "error": str(e),
                "success": False
            }    