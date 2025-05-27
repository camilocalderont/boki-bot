"""
Módulo de gestión de conversaciones para WhatsApp Bot.

"""

# Importación principal para compatibilidad con código existente
from .conversation_manager import ConversationManager

# Componentes internos (para testing o uso avanzado)
from .message_processor import MessageProcessor
from .flow_router import FlowRouter
from .button_handler import ButtonHandler
from .unknown_handler import UnknownIntentHandler

# Export principal para el webhook
__all__ = [
    # Clase principal - usada por webhook
    "ConversationManager",
    
    # Componentes internos - para testing/debugging
    "MessageProcessor", 
    "FlowRouter",
    "ButtonHandler",
    "UnknownIntentHandler"
]
