import aiohttp
import time
from typing import Dict
from .base_llm import BaseLLM, LLMResponse, LLMError


class OllamaProvider(BaseLLM):
    """
    Proveedor que conecta con Ollama para usar TinyLlama y Mistral.
    """

    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 30):
        super().__init__()
        self.base_url = base_url
        self.timeout = timeout
        self.session = None
        
        # Modelos específicos para tu flujo
        self.intent_model = "tinyllama:1.1b"      # Para detección rápida
        self.conversation_model = "mistral:7b-instruct"  # Para conversación

    async def __aenter__(self):
        """Context manager para manejar la sesión HTTP."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cierra la sesión HTTP."""
        if self.session:
            await self.session.close()

    async def generate_response(
        self,
        prompt: str,
        model_name: str,
        max_tokens: int = 150,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Genera respuesta usando Ollama."""
        if not self.session:
            raise LLMError("Sesión no inicializada. Usa 'async with' o llama __aenter__")

        start_time = time.time()
        
        try:
            # Payload para Ollama
            data = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": 0.9,
                    "stop": ["\n\n", "Usuario:", "Asistente:"]  # Parar en estos tokens
                }
            }

            self.logger.debug(f"[OLLAMA] Enviando a {model_name}: {prompt[:100]}...")

            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise LLMError(f"Ollama error {response.status}: {error_text}")
                
                result = await response.json()
                
                generated_text = result.get("response", "").strip()
                
                if not generated_text:
                    raise LLMError("Ollama devolvió respuesta vacía")

                response_time = time.time() - start_time
                
                return LLMResponse(
                    text=generated_text,
                    model=model_name,
                    tokens_used=result.get("eval_count", 0),
                    response_time=response_time,
                    metadata={
                        "eval_duration": result.get("eval_duration", 0),
                        "total_duration": result.get("total_duration", 0)
                    }
                )

        except Exception as e:
            self.logger.error(f"[OLLAMA] Error generando respuesta: {e}")
            raise LLMError(f"Error en Ollama: {str(e)}")

    async def is_available(self) -> bool:
        """Verifica si Ollama está disponible."""
        try:
            if not self.session:
                # Crear sesión temporal para verificar
                async with aiohttp.ClientSession() as temp_session:
                    async with temp_session.get(f"{self.base_url}/api/version") as response:
                        return response.status == 200
            else:
                async with self.session.get(f"{self.base_url}/api/version") as response:
                    return response.status == 200
        except:
            return False

    async def detect_intent(self, message: str, context: str = "") -> LLMResponse:
        """Método específico para detección de intenciones con TinyLlama."""
        prompt = f"""Clasifica la intención del usuario en un bot de WhatsApp para clínica de belleza.

REGLAS:
- Responde SOLO con UNA palabra
- APPOINTMENT = agendar, cancelar, modificar citas
- FAQ = preguntas sobre servicios, precios, horarios
- SUPPORT = problemas, quejas, errores
- CONTINUE_FLOW = quiere continuar proceso anterior
- GENERAL = saludos, conversación general

Contexto: {context}
Mensaje: "{message}"

Clasificación:"""

        return await self.generate_response(
            prompt=prompt,
            model_name=self.intent_model,
            max_tokens=5,  # Reducido para forzar respuesta corta
            temperature=0.1  # Muy baja para respuesta determinística
        )

    async def generate_welcome_message(
        self, 
        user_name: str,
        last_conversation: str,
        has_active_flow: bool,
        flow_type: str = "",
        same_day: bool = False
    ) -> LLMResponse:
        """Método específico para generar saludo de bienvenida con Mistral."""
        
        time_context = "hoy mismo" if same_day else "hace un tiempo"
        flow_context = ""
        
        if has_active_flow:
            flow_context = f"Tienes un proceso de {flow_type} pendiente. "
        
        prompt = f"""Eres un asistente virtual amigable de una clínica de belleza en Colombia.

        Usuario: {user_name}
        Última conversación: {last_conversation}
        Conversamos: {time_context}
        {flow_context}

        Genera un saludo corto y natural que:
        1. Salude apropiadamente según si hablamos hoy o no
        2. Si hay flujo pendiente, pregunte si quiere continuar
        3. Si no hay flujo, pregunte en qué puede ayudar
        4. Máximo 2 líneas, tono amigable y profesional

        Saludo:"""

        return await self.generate_response(
            prompt=prompt,
            model_name=self.conversation_model,
            max_tokens=100,
            temperature=0.8
        )