from typing import List, Dict, Union
from .buttons import WhatsAppButtons
from .lists import WhatsAppLists

class WhatsAppHelper:
    """
    Helper unificado que decide automáticamente entre botones o listas.
    Responsabilidad única: automatizar la elección del mejor formato según la cantidad de opciones.
    """
    
    @staticmethod
    def create_interactive_response(text: str, options: List[Dict], button_text: str = "Seleccionar", section_title: str = "Opciones", force_list: bool = False) -> Dict:
        """
        Crea automáticamente botones o lista según la cantidad de opciones.
        
        Args:
            text: Texto del mensaje
            options: Lista de opciones con formato [{"id": "1", "title": "Opción 1", "description": "..."}]
            button_text: Texto del botón (solo para listas)
            section_title: Título de la sección (solo para listas)
            force_list: Forzar uso de lista aunque haya pocas opciones
            
        Returns:
            Dict: Estructura de mensaje (botones o lista según convenga)
        """
        if not options:
            raise ValueError("Debe proporcionar al menos una opción")
        
        # Decidir formato automáticamente
        use_buttons = WhatsAppButtons.can_use_buttons(len(options)) and not force_list
        
        if use_buttons:
            # Usar botones (hasta 3 opciones)
            return WhatsAppButtons.create_buttons_response(text, options)
        else:
            # Usar lista (4+ opciones o forzado)
            return WhatsAppLists.create_list_response(text, options, button_text, section_title)
    
    @staticmethod
    def create_simple_interactive(text: str, items: List[tuple], button_text: str = "Seleccionar", section_title: str = "Opciones", force_list: bool = False) -> Dict:
        """
        Versión simplificada usando tuplas.
        
        Args:
            text: Texto del mensaje
            items: Lista de tuplas (id, title) o (id, title, description)
            button_text: Texto del botón (solo para listas)
            section_title: Título de la sección (solo para listas)
            force_list: Forzar uso de lista
            
        Returns:
            Dict: Estructura de mensaje (botones o lista)
            
        Example:
            # Se decidirá automáticamente entre botones o lista
            response = create_simple_interactive(
                "Elige una categoría:",
                [
                    ("cat1", "Manicure", "Servicios de uñas"),
                    ("cat2", "Pedicure", "Cuidado de pies"),
                    ("cat3", "Facial", "Tratamientos faciales")
                ]
            )
        """
        # Convertir tuplas a formato de opciones
        options = []
        for item in items:
            if len(item) == 2:
                item_id, title = item
                description = ""
            elif len(item) == 3:
                item_id, title, description = item
            else:
                raise ValueError("Los items deben ser tuplas de 2 o 3 elementos")
            
            options.append({
                "id": item_id,
                "title": title,
                "description": description
            })
        
        return WhatsAppHelper.create_interactive_response(
            text, options, button_text, section_title, force_list
        )
    
    @staticmethod
    def create_confirmation(
        text: str,
        yes_id: str = "confirm_yes",
        no_id: str = "confirm_no"
    ) -> Dict:
        """
        Crea botones de confirmación (siempre botones, nunca lista).
        
        Args:
            text: Texto del mensaje
            yes_id: ID del botón de confirmación
            no_id: ID del botón de cancelación
            
        Returns:
            Dict: Estructura de mensaje con botones de confirmación
        """
        return WhatsAppButtons.create_confirmation_buttons(text, yes_id, no_id)