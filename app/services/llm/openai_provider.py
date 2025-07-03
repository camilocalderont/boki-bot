import openai
import time
import logging
import os
from typing import Optional, Dict, Any
from .base_llm import BaseLLM, LLMResponse, LLMError

logger = logging.getLogger(__name__)

class OpenAIProvider(BaseLLM):
    """
    Proveedor OpenAI para detección de intención y respuestas naturales.
    """

    def __init__(self):
        self.client = None
        self.api_key = os.getenv("LLM_APIKEY")  # Usa tu clave existente
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")  # Modelo económico y rápido
        
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY no configurada")

    async def __aenter__(self):
        """Inicializa el cliente de OpenAI."""
        try:
            openai.api_key = self.api_key
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
            logger.info("[OPENAI] Cliente inicializado correctamente")
            return self
        except Exception as e:
            logger.error(f"[OPENAI] Error inicializando cliente: {e}")
            raise LLMError(f"Error inicializando OpenAI: {e}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Limpia recursos."""
        self.client = None

    async def generate_response(
        self, 
        prompt: str, 
        model_name: str = None,
        max_tokens: int = 150,
        temperature: float = 0.3
    ) -> LLMResponse:
        """Genera respuesta usando OpenAI."""
        if not self.client:
            raise LLMError("Cliente OpenAI no inicializado")

        start_time = time.time()
        model = model_name or self.model

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9
            )

            content = response.choices[0].message.content.strip()
            response_time = time.time() - start_time

            return LLMResponse(
                text=content,
                model=model,
                tokens_used=response.usage.total_tokens,
                response_time=response_time,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens
                }
            )

        except Exception as e:
            logger.error(f"[OPENAI] Error generando respuesta: {e}")
            raise LLMError(f"Error en OpenAI: {str(e)}")

    async def detect_intent(self, message: str, context: str = "") -> LLMResponse:
        """
        Detecta intención usando GPT con prompt especializado.
        """
        prompt = self._create_intent_detection_prompt(message, context)
        
        try:
            response = await self.generate_response(
                prompt=prompt,
                max_tokens=50,  # Respuesta corta para intención
                temperature=0.1  # Más determinístico
            )
            
            # Extraer intención limpia de la respuesta
            intent = self._parse_intent_response(response.text)
            
            return LLMResponse(
                text=intent,
                model=response.model,
                tokens_used=response.tokens_used,
                response_time=response.response_time,
                metadata=response.metadata
            )
            
        except Exception as e:
            logger.error(f"[OPENAI] Error detectando intención: {e}")
            raise LLMError(f"Error en detección de intención: {str(e)}")

    def _create_intent_detection_prompt(self, message: str, context: str = "") -> str:
        """Crea prompt especializado para detección de intención."""
        base_prompt = """Eres un asistente especializado en clasificar las intenciones de usuarios que escriben a un chatbot de una clínica médica/estética.

INTENCIONES DISPONIBLES:
- APPOINTMENT: Usuario quiere agendar, modificar, cancelar o consultar citas
- FAQ: Usuario hace preguntas sobre servicios, precios, ubicación, horarios
- SUPPORT: Usuario tiene problemas técnicos o necesita ayuda con el sistema
- END_CONVERSATION: Usuario quiere terminar la conversación o despedirse
- UNKNOWN: Mensaje no relacionado con los servicios médicos

REGLAS:
1. Responde SOLO con el nombre de la intención en MAYÚSCULAS
2. Si hay dudas entre dos intenciones, elige la más específica
3. Palabras clave para APPOINTMENT: "agendar", "cita", "hora", "cancelar", "reagendar", "consulta médica"
4. Palabras clave para FAQ: "qué", "cuánto", "dónde", "cuándo", "cómo", "servicios", "precios"
5. Para saludos simples sin intención clara: FAQ

CONTEXTO PREVIO:
{context}

MENSAJE A CLASIFICAR:
"{message}"

INTENCIÓN:"""

        return base_prompt.format(
            context=context if context else "Sin contexto previo",
            message=message
        )

    def _parse_intent_response(self, response: str) -> str:
        """Extrae la intención de la respuesta de GPT."""
        # Limpiar respuesta
        intent = response.strip().upper()
        
        # Mapear posibles variaciones
        intent_mapping = {
            "CITA": "APPOINTMENT",
            "AGENDAR": "APPOINTMENT", 
            "CONSULTA": "APPOINTMENT",
            "PREGUNTA": "FAQ",
            "INFORMACIÓN": "FAQ",
            "INFO": "FAQ",
            "AYUDA": "SUPPORT",
            "PROBLEMA": "SUPPORT",
            "TERMINAR": "END_CONVERSATION",
            "SALIR": "END_CONVERSATION",
            "DESPEDIDA": "END_CONVERSATION"
        }
        
        # Buscar intención válida
        valid_intents = ["APPOINTMENT", "FAQ", "SUPPORT", "END_CONVERSATION", "UNKNOWN"]
        
        if intent in valid_intents:
            return intent
        elif intent in intent_mapping:
            return intent_mapping[intent]
        else:
            # Buscar palabras clave en la respuesta
            response_lower = response.lower()
            if any(word in response_lower for word in ["appointment", "cita", "agendar"]):
                return "APPOINTMENT"
            elif any(word in response_lower for word in ["faq", "pregunta", "información"]):
                return "FAQ"
            elif any(word in response_lower for word in ["support", "ayuda", "problema"]):
                return "SUPPORT"
            elif any(word in response_lower for word in ["end", "terminar", "despedida"]):
                return "END_CONVERSATION"
            else:
                return "UNKNOWN"

    async def is_available(self) -> bool:
        """Verifica disponibilidad del servicio OpenAI."""
        try:
            if not self.client:
                return False
                
            # Test simple para verificar conectividad
            await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.warning(f"[OPENAI] No disponible: {e}")
            return False