from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    """Respuesta de un modelo LLM."""
    text: str
    model: str
    tokens_used: int = 0
    response_time: float = 0.0
    metadata: Dict[str, Any] = None
    
class LLMError(Exception):
    """Error específico de LLM."""
    pass

class BaseLLM(ABC):
    """Interfaz base para todos los proveedores LLM."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def generate_response(
        self, 
        prompt: str,
        model_name: str,
        max_tokens: int = 150,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Genera respuesta usando el modelo especificado."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Verifica si el proveedor está disponible."""
        pass