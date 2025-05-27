"""
Módulo para generar componentes interactivos de WhatsApp.
Automatiza la creación de botones y listas respetando los límites de la API.
"""

from .buttons import WhatsAppButtons
from .lists import WhatsAppLists
from .helper import WhatsAppHelper

# Exports principales para uso directo
__all__ = [
    'WhatsAppButtons',
    'WhatsAppLists', 
    'WhatsAppHelper'
]

# Funciones de conveniencia para importación rápida
create_interactive = WhatsAppHelper.create_interactive_response
create_simple_interactive = WhatsAppHelper.create_simple_interactive
create_confirmation = WhatsAppHelper.create_confirmation

# Funciones específicas para casos avanzados
create_buttons = WhatsAppButtons.create_buttons_response
create_list = WhatsAppLists.create_list_response
create_categorized_list = WhatsAppLists.create_categorized_list