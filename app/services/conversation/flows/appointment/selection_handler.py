import logging
import re
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class SelectionHandler:
    """
    Responsabilidad única: Extraer y validar selecciones de usuario.
    """

    @staticmethod
    def extract_user_selection(message: str, options_data: List[Dict]) -> Optional[Dict]:
        """
        Extrae la selección del usuario y retorna el objeto seleccionado.
        """
        logger.debug(f"Extrayendo selección de: '{message}'")
        
        if not message:
            logger.warning("Mensaje está vacío o es None")
            return None
        
        message_clean = message.strip()
        
        # 1. Búsqueda por ID directo (botones de WhatsApp)
        selection = SelectionHandler._find_by_button_id(message_clean, options_data)
        if selection:
            return selection
        
        # 2. Búsqueda por título exacto
        selection = SelectionHandler._find_by_exact_title(message_clean, options_data)
        if selection:
            return selection
        
        # 3. Búsqueda por índice numérico
        selection = SelectionHandler._find_by_index(message_clean, options_data)
        if selection:
            return selection
        
        # 4. Búsqueda por coincidencia parcial (fallback)
        selection = SelectionHandler._find_by_partial_match(message_clean, options_data)
        if selection:
            return selection
        
        # 5. Búsqueda por nombre de profesional
        selection = SelectionHandler._find_by_professional_name(message_clean, options_data)
        if selection:
            return selection
        
        logger.warning(f"No se pudo extraer selección de: '{message}'")
        return None

    @staticmethod
    def _find_by_button_id(message: str, options_data: List[Dict]) -> Optional[Dict]:
        """Busca por ID de botón directo."""
        for option in options_data:
            if message == option.get('button_id'):
                logger.debug(f"Selección por ID: {message}")
                return option
        return None

    @staticmethod
    def _find_by_exact_title(message: str, options_data: List[Dict]) -> Optional[Dict]:
        """Busca por título exacto."""
        message_lower = message.lower()
        for option in options_data:
            if 'data' in option:
                title = option['data'].get('VcName', '') or ''
                title = title.strip().lower()
                if message_lower == title:
                    logger.debug(f"Selección por título exacto: '{message}'")
                    return option
        return None

    @staticmethod
    def _find_by_index(message: str, options_data: List[Dict]) -> Optional[Dict]:
        """Busca por índice numérico."""
        try:
            selection = int(message)
            if 1 <= selection <= len(options_data):
                selected_option = options_data[selection - 1]
                logger.debug(f"Selección por número: {selection}")
                return selected_option
        except ValueError:
            pass
        return None

    @staticmethod
    def _find_by_partial_match(message: str, options_data: List[Dict]) -> Optional[Dict]:
        """Busca por coincidencia parcial en título."""
        message_lower = message.lower()
        for option in options_data:
            if 'data' in option:
                title = option['data'].get('VcName', '').lower()
                if message_lower in title or title in message_lower:
                    logger.debug(f"Selección por coincidencia parcial: '{message}'")
                    return option
        return None

    @staticmethod
    def _find_by_professional_name(message: str, options_data: List[Dict]) -> Optional[Dict]:
        """Busca por nombre completo de profesional."""
        message_lower = message.lower()
        for option in options_data:
            if 'data' in option:
                professional = option['data']
                # Si tiene campos de profesional, construir nombre completo
                if 'VcFirstName' in professional:
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
                    
                    full_name = ' '.join(name_parts).lower()
                    if message_lower == full_name or message_lower in full_name:
                        logger.debug(f"Selección por nombre de profesional: '{message}'")
                        return option
        return None
