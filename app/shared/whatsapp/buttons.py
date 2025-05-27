from typing import List, Dict, Union

class WhatsAppButtons:
    """
    Factory para crear botones interactivos de WhatsApp.
    Responsabilidad única: generar estructuras de botones válidas para WhatsApp.
    """
    
    MAX_BUTTONS = 3  # WhatsApp limita a 3 botones por mensaje
    MAX_TITLE_LENGTH = 20  # Máximo 20 caracteres para título de botón
    
    @staticmethod
    def create_buttons_response(text: str, buttons: List[Dict]) -> Dict:
        """
        Crea una respuesta con botones para WhatsApp.
        
        Args:
            text: Texto del mensaje
            buttons: Lista de botones con formato [{"id": "1", "title": "Opción 1"}, ...]
            
        Returns:
            Dict: Estructura de mensaje con botones para WhatsApp
            
        Raises:
            ValueError: Si hay más de 3 botones o títulos muy largos
        """
        if len(buttons) > WhatsAppButtons.MAX_BUTTONS:
            raise ValueError(f"WhatsApp permite máximo {WhatsAppButtons.MAX_BUTTONS} botones, recibidos: {len(buttons)}")
        
        if not buttons:
            raise ValueError("Debe proporcionar al menos un botón")
        
        # Validar y truncar títulos si es necesario
        validated_buttons = []
        for btn in buttons:
            if not btn.get("id") or not btn.get("title"):
                raise ValueError("Cada botón debe tener 'id' y 'title'")
            
            validated_buttons.append({
                "type": "reply",
                "reply": {
                    "id": btn["id"],
                    "title": btn["title"][:WhatsAppButtons.MAX_TITLE_LENGTH]
                }
            })
        
        return {
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text},
                "action": {
                    "buttons": validated_buttons
                }
            }
        }
    
    @staticmethod
    def create_simple_buttons(text: str, button_data: List[tuple]) -> Dict:
        """
        Crea botones de forma simplificada usando tuplas.
        
        Args:
            text: Texto del mensaje
            button_data: Lista de tuplas (id, title) 
            
        Returns:
            Dict: Estructura de mensaje con botones
            
        Example:
            buttons = create_simple_buttons(
                "Elige una opción:",
                [("opt1", "Opción 1"), ("opt2", "Opción 2")]
            )
        """
        buttons = [
            {"id": btn_id, "title": title}
            for btn_id, title in button_data
        ]
        return WhatsAppButtons.create_buttons_response(text, buttons)
    
    @staticmethod
    def create_confirmation_buttons(text: str, yes_id: str = "confirm_yes", no_id: str = "confirm_no") -> Dict:
        """
        Crea botones de confirmación estándar (Sí/No).
        
        Args:
            text: Texto del mensaje
            yes_id: ID del botón de confirmación
            no_id: ID del botón de cancelación
            
        Returns:
            Dict: Estructura de mensaje con botones de confirmación
        """
        buttons = [
            {"id": yes_id, "title": "✅ Sí, confirmar"},
            {"id": no_id, "title": "❌ Cancelar"}
        ]
        return WhatsAppButtons.create_buttons_response(text, buttons)
    
    @staticmethod
    def can_use_buttons(items_count: int) -> bool:
        """
        Verifica si se pueden usar botones según la cantidad de elementos.
        
        Args:
            items_count: Cantidad de elementos a mostrar
            
        Returns:
            bool: True si se pueden usar botones, False si se debe usar lista
        """
        return items_count <= WhatsAppButtons.MAX_BUTTONS