import logging
from typing import Optional
from ..llm.openai_provider import OpenAIProvider, LLMError
from .detector import EnhancedIntentDetector as BaseDetector, Intent

logger = logging.getLogger(__name__)

class GPTIntentDetector:
    """
    Detector de intención usando OpenAI GPT como primario y embeddings como fallback.
    """

    def __init__(self):
        self.openai_provider: Optional[OpenAIProvider] = None
        self.fallback_detector = BaseDetector()  # Tu detector actual
        self._is_openai_available = False

    async def initialize(self):
        """Inicializa el detector con OpenAI."""
        try:
            self.openai_provider = OpenAIProvider()
            await self.openai_provider.__aenter__()
            
            # Verificar disponibilidad
            self._is_openai_available = await self.openai_provider.is_available()
            
            if self._is_openai_available:
                logger.info("🤖 [GPT_INTENT] OpenAI inicializado correctamente")
            else:
                logger.warning("⚠️ [GPT_INTENT] OpenAI no disponible, usando fallback")
                
        except Exception as e:
            logger.error(f"❌ [GPT_INTENT] Error inicializando OpenAI: {e}")
            self._is_openai_available = False

    async def detect_intent(self, message: str, context: str = "") -> Intent:
        """
        Detecta intención con estrategia híbrida: OpenAI -> Fallback.
        """
        # Estrategia 1: Intentar con OpenAI
        if self._is_openai_available and self.openai_provider:
            try:
                response = await self.openai_provider.detect_intent(message, context)
                intent_str = response.text.strip().upper()
                
                # Convertir string a enum
                intent = self._string_to_intent(intent_str)
                
                if intent != Intent.UNKNOWN:
                    logger.info(f"🎯 [GPT_INTENT] OpenAI detectó: {intent.name}")
                    return intent
                else:
                    logger.warning(f"⚠️ [GPT_INTENT] OpenAI devolvió intent desconocido: {intent_str}")
                    
            except Exception as e:
                logger.warning(f"⚠️ [GPT_INTENT] OpenAI falló, usando fallback: {e}")
                # Marcar como no disponible para esta sesión
                self._is_openai_available = False

        # Estrategia 2: Fallback al detector actual
        logger.info("🔄 [GPT_INTENT] Usando detector con embeddings")
        try:
            fallback_intent = self.fallback_detector.detect_intent(message)
            logger.info(f"🛡️ [GPT_INTENT] Fallback detectó: {fallback_intent.name}")
            return fallback_intent
        except Exception as e:
            logger.error(f"❌ [GPT_INTENT] Fallback falló: {e}")
            return Intent.UNKNOWN

    def _string_to_intent(self, intent_str: str) -> Intent:
        """Convierte string de intención a enum."""
        # Limpiar la string
        intent_str = intent_str.strip().upper()
        
        # Mapeo directo
        intent_mapping = {
            "APPOINTMENT": Intent.APPOINTMENT,
            "FAQ": Intent.FAQ,
            "SUPPORT": Intent.SUPPORT,
            "END_CONVERSATION": Intent.END_CONVERSATION,
            "UNKNOWN": Intent.UNKNOWN
        }
        
        # Mapeo adicional en español (por si OpenAI responde en español)
        spanish_mapping = {
            "CITA": Intent.APPOINTMENT,
            "AGENDAR": Intent.APPOINTMENT,
            "CONSULTA": Intent.APPOINTMENT,
            "PREGUNTA": Intent.FAQ,
            "INFORMACIÓN": Intent.FAQ,
            "INFO": Intent.FAQ,
            "AYUDA": Intent.SUPPORT,
            "PROBLEMA": Intent.SUPPORT,
            "SOPORTE": Intent.SUPPORT,
            "TERMINAR": Intent.END_CONVERSATION,
            "SALIR": Intent.END_CONVERSATION,
            "DESPEDIDA": Intent.END_CONVERSATION,
            "CHAO": Intent.END_CONVERSATION
        }
        
        # Buscar en mapeos
        if intent_str in intent_mapping:
            return intent_mapping[intent_str]
        elif intent_str in spanish_mapping:
            return spanish_mapping[intent_str]
        
        # Búsqueda parcial (por si la respuesta contiene palabras adicionales)
        for key, intent in {**intent_mapping, **spanish_mapping}.items():
            if key in intent_str or intent_str in key:
                return intent
        
        # Si no encuentra nada
        return Intent.UNKNOWN

    async def cleanup(self):
        """Limpia recursos."""
        try:
            if self.openai_provider:
                await self.openai_provider.__aexit__(None, None, None)
                self.openai_provider = None
            self._is_openai_available = False
            logger.debug("[GPT_INTENT] Recursos liberados")
        except Exception as e:
            logger.warning(f"[GPT_INTENT] Error en cleanup: {e}")

    @property
    def is_available(self) -> bool:
        """Indica si OpenAI está disponible"""
        return self._is_openai_available