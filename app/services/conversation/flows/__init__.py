# ================================
# 6. app/services/conversation/flows/__init__.py (SIMPLIFICADO)
# ================================
"""
Módulo de flujos de conversación para WhatsApp Bot.

Arquitectura híbrida aplicando principios SOLID:
- Flujos complejos: En carpetas separadas (appointment/, registration/)
- Flujos simples: Archivos individuales

Uso:
    from app.services.conversation.flows import AppointmentFlow, RegistrationFlow
"""

# ================================
# CLASE BASE
# ================================
from .base_flow import BaseFlow

# ================================
# FLUJOS COMPLEJOS (en carpetas)
# ================================

# Appointment Flow - Refactorizado en carpeta especializada
from .appointment import AppointmentFlow

# Registration Flow - Refactorizado en carpeta especializada  
from .registration import RegistrationFlow

# ================================
# FLUJOS SIMPLES (archivos individuales)
# ================================

# Flujos que pueden permanecer como archivos únicos por su simplicidad
from .faq_flow import FAQFlow
from .end_conversation_flow import EndConversationFlow
from .support_flow import SupportFlow

# ================================
# EXPORTS PRINCIPALES
# ================================

__all__ = [
    # Clase base
    "BaseFlow",
    
    # Flujos principales
    "AppointmentFlow",      # ✅ Refactorizado en carpeta
    "RegistrationFlow",     # ✅ Refactorizado en carpeta
    "FAQFlow",             # 📄 Archivo individual  
    "EndConversationFlow",  # 📄 Archivo individual
    "SupportFlow",         # 📄 Archivo individual
]

# ================================
# CONFIGURACIÓN DEL MÓDULO
# ================================

__version__ = "2.0.0"  # Arquitectura híbrida con SRP

# Mapping para uso dinámico en conversation_manager
FLOW_MAPPING = {
    "appointment": AppointmentFlow,
    "registration": RegistrationFlow,
    "faq": FAQFlow,
    "end_conversation": EndConversationFlow,
    "support": SupportFlow
}

def get_flow_class(flow_name: str):
    """
    Obtiene la clase de flujo por nombre.
    Útil para instanciación dinámica.
    """
    return FLOW_MAPPING.get(flow_name)