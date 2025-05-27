from typing import List, Dict, Optional

class WhatsAppLists:
    """
    Factory para crear listas interactivas de WhatsApp.
    Responsabilidad única: generar estructuras de listas válidas para WhatsApp.
    """
    
    MAX_SECTION_TITLE_LENGTH = 24  # Máximo 24 caracteres para título de sección
    MAX_ROW_TITLE_LENGTH = 20      # Máximo 20 caracteres para título de fila
    MAX_ROW_DESCRIPTION_LENGTH = 72 # Máximo 72 caracteres para descripción de fila
    MAX_BUTTON_TEXT_LENGTH = 20    # Máximo 20 caracteres para texto del botón
    
    @staticmethod
    def create_list_response(
        text: str, 
        options: List[Dict], 
        button_text: str = "Seleccionar",
        section_title: str = "Opciones"
    ) -> Dict:
        """
        Crea una respuesta con lista para WhatsApp.
        
        Args:
            text: Texto del mensaje
            options: Lista de opciones con formato [{"id": "1", "title": "Opción 1", "description": "..."}]
            button_text: Texto del botón principal
            section_title: Título de la sección
            
        Returns:
            Dict: Estructura de mensaje con lista para WhatsApp
            
        Raises:
            ValueError: Si no hay opciones o faltan campos requeridos
        """
        if not options:
            raise ValueError("Debe proporcionar al menos una opción")
        
        # Validar y truncar campos
        validated_rows = []
        for opt in options:
            if not opt.get("id") or not opt.get("title"):
                raise ValueError("Cada opción debe tener 'id' y 'title'")
            
            validated_rows.append({
                "id": opt["id"],
                "title": opt["title"][:WhatsAppLists.MAX_ROW_TITLE_LENGTH],
                "description": opt.get("description", "")[:WhatsAppLists.MAX_ROW_DESCRIPTION_LENGTH]
            })
        
        return {
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": text},
                "action": {
                    "button": button_text[:WhatsAppLists.MAX_BUTTON_TEXT_LENGTH],
                    "sections": [{
                        "title": section_title[:WhatsAppLists.MAX_SECTION_TITLE_LENGTH],
                        "rows": validated_rows
                    }]
                }
            }
        }
    
    @staticmethod
    def create_simple_list(
        text: str, 
        items: List[tuple], 
        button_text: str = "Seleccionar",
        section_title: str = "Opciones"
    ) -> Dict:
        """
        Crea una lista de forma simplificada usando tuplas.
        
        Args:
            text: Texto del mensaje
            items: Lista de tuplas (id, title) o (id, title, description)
            button_text: Texto del botón principal
            section_title: Título de la sección
            
        Returns:
            Dict: Estructura de mensaje con lista
            
        Example:
            list_msg = create_simple_list(
                "Elige una opción:",
                [
                    ("opt1", "Opción 1", "Descripción 1"),
                    ("opt2", "Opción 2", "Descripción 2")
                ]
            )
        """
        options = []
        for item in items:
            if len(item) == 2:
                # (id, title)
                item_id, title = item
                description = ""
            elif len(item) == 3:
                # (id, title, description)
                item_id, title, description = item
            else:
                raise ValueError("Los items deben ser tuplas de 2 o 3 elementos: (id, title) o (id, title, description)")
            
            options.append({
                "id": item_id,
                "title": title,
                "description": description
            })
        
        return WhatsAppLists.create_list_response(text, options, button_text, section_title)
    
    @staticmethod
    def create_categorized_list(
        text: str,
        categories: Dict[str, List[Dict]],
        button_text: str = "Seleccionar"
    ) -> Dict:
        """
        Crea una lista con múltiples secciones/categorías.
        
        Args:
            text: Texto del mensaje
            categories: Dict donde key=título_sección y value=lista_opciones
            button_text: Texto del botón principal
            
        Returns:
            Dict: Estructura de mensaje con lista multi-sección
            
        Example:
            list_msg = create_categorized_list(
                "Elige un servicio:",
                {
                    "Manicure": [{"id": "m1", "title": "Básica"}, {"id": "m2", "title": "Premium"}],
                    "Pedicure": [{"id": "p1", "title": "Clásica"}, {"id": "p2", "title": "Spa"}]
                }
            )
        """
        sections = []
        for section_title, section_options in categories.items():
            if not section_options:
                continue
                
            validated_rows = []
            for opt in section_options:
                if not opt.get("id") or not opt.get("title"):
                    continue
                    
                validated_rows.append({
                    "id": opt["id"],
                    "title": opt["title"][:WhatsAppLists.MAX_ROW_TITLE_LENGTH],
                    "description": opt.get("description", "")[:WhatsAppLists.MAX_ROW_DESCRIPTION_LENGTH]
                })
            
            if validated_rows:
                sections.append({
                    "title": section_title[:WhatsAppLists.MAX_SECTION_TITLE_LENGTH],
                    "rows": validated_rows
                })
        
        if not sections:
            raise ValueError("Debe haber al menos una sección con opciones válidas")
        
        return {
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": text},
                "action": {
                    "button": button_text[:WhatsAppLists.MAX_BUTTON_TEXT_LENGTH],
                    "sections": sections
                }
            }
        }