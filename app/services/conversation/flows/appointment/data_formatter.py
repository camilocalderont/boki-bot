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
        Convierte fecha del backend al formato MM/DD/YYYY para la API.
        
        Args:
            date_info: Objeto del backend con 'fechaCompleta'
            
        Returns:
            str: Fecha en formato MM/DD/YYYY o None si hay error
        """
        try:
            fecha_completa = date_info.get('fechaCompleta', '')
            if fecha_completa:
                # "27/05/2025 00:00" -> "05/27/2025"
                fecha_parte = fecha_completa.split()[0]  # "27/05/2025"
                dia, mes, año = fecha_parte.split('/')
                return f"{mes}/{dia}/{año}"
            return None
        except Exception as e:
            logger.warning(f"Error convirtiendo fecha para API: {e}")
            return None