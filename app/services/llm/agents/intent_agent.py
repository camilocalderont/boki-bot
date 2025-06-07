# app/services/llm/agents/intent_agent.py
from ..providers.base import load_agent_config
from ..providers.llamacpp import LlamaCppProvider
from ..prompt_replacers.intent_replacer import IntentReplacer

class IntentAgent:
    """Detector de intenciones simple"""
    
    def __init__(self, llm_api_service):
        self.llm_api = llm_api_service
    
    async def detect_intent(self, user_message: str, company_id: str) -> str:
        """
        Detecta intención - simple y directo
        """
        try:
            # Cargar configuración desde BD
            config = await load_agent_config(self.llm_api, company_id, "intent_detection")
            
            if not config:
                return "UNKNOWN"
            
            if not config.get('is_active', True):
                return "UNKNOWN"
            
            # Construir contexto para reemplazos
            context = {'user_message': user_message}
            
            # Procesar prompt usando el sistema de reemplazos
            prompt = await self._build_prompt(config, context)
            
            # Inicializar proveedor con configuración dinámica
            provider = LlamaCppProvider()
            await provider.initialize(config)
            
            # Generar respuesta
            response = await provider.generate(prompt)
            
            if response.success:
                # DEBUG: Imprimir respuesta cruda
                print(f"🔍 DEBUG - Respuesta cruda del LLM: '{response.text}'")
                
                # Procesar respuesta para extraer intención
                intent = self._extract_intent(response.text)
                return intent
            else:
                print(f"🔍 DEBUG - Error en LLM: {response.error}")
                return "UNKNOWN"
                
        except Exception as e:
            print(f"🔍 DEBUG - Excepción: {e}")
            return "UNKNOWN"
    
    async def _build_prompt(self, config: dict, context: dict) -> str:
        """
        Construye prompt simple
        """
        prompt_template = config.get('prompt_template', '')
        
        if not prompt_template:
            raise ValueError("No hay template de prompt configurado en la BD")
        
        final_prompt = await IntentReplacer.replace_variables(prompt_template, context)
        
        return final_prompt
    
    def _extract_intent(self, llm_response: str) -> str:
        """
        Extrae la intención de la respuesta del LLM
        """
        # Limpiar respuesta
        intent = llm_response.strip().upper()
        
        # Intenciones válidas
        valid_intents = {'APPOINTMENT', 'FAQ', 'SUPPORT', 'GREETING', 'END_CONVERSATION', 'UNKNOWN'}
        
        # Buscar intención válida en la respuesta
        for valid_intent in valid_intents:
            if valid_intent in intent:
                return valid_intent
        
        # Si no encuentra intención válida, retornar UNKNOWN
        return "UNKNOWN"