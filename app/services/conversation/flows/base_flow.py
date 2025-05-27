from abc import ABC, abstractmethod
from typing import Tuple, Dict, Union, Optional
import logging

class BaseFlow(ABC):
    """
    Clase base para todos los flujos de conversación.
    
    Responsabilidad: Definir interfaz común y utilidades compartidas.
    Todos los flujos específicos deben heredar de esta clase.
    """

    def __init__(self):
        """Inicialización base. Los flujos hijos pueden sobrescribir."""
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def process_message(self, state: Dict, message: str, contact_id: str) -> Tuple[Dict, Union[str, Dict], bool]:
        """
        Procesa un mensaje dentro del flujo.

        Args:
            state: Estado actual de la conversación
            message: Mensaje del usuario
            contact_id: ID del contacto

        Returns:
            Tuple[Dict, Union[str, Dict], bool]: 
                - nuevo_estado: Estado actualizado
                - respuesta: Respuesta para el usuario (str o dict para WhatsApp)
                - flujo_completado: True si el flujo terminó
        """
        pass

    def log_step(self, step: str, contact_id: str, message: str = ""):
        """Utilidad para logging consistente entre flujos."""
        flow_name = self.__class__.__name__.replace('Flow', '').upper()
        self.logger.info(f"[{flow_name}] Paso '{step}' - Contacto: {contact_id}")
        if message:
            self.logger.debug(f"[{flow_name}] Mensaje: '{message}'")

    def create_error_response(self, error_message: str, current_state: Dict) -> Tuple[Dict, str, bool]:
        """Utilidad para respuestas de error consistentes."""
        return (
            current_state,
            f"❌ {error_message}",
            False
        )

    def create_completion_response(self, success_message: str) -> Tuple[Dict, str, bool]:
        """Utilidad para respuestas de completación."""
        return (
            {},  # Estado vacío = flujo completado
            f"✅ {success_message}",
            True  # Flujo completado
        )