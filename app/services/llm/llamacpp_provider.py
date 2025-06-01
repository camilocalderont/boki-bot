"""
Provider LlamaCpp que implementa la interfaz BaseLLM existente.
Reemplazo directo de OllamaProvider sin cambiar la interfaz.
"""

import logging
import time
from typing import Dict, Optional
from pathlib import Path

from .base_llm import BaseLLM, LLMResponse, LLMError
from .model_downloader import ModelDownloader

logger = logging.getLogger(__name__)

class LlamaCppProvider(BaseLLM):
    """
    Proveedor LlamaCpp que mantiene la misma interfaz que OllamaProvider.
    Drop-in replacement para el sistema existente.
    """

    def __init__(self, models_dir: str = "models"):
        super().__init__()
        self.models_dir = Path(models_dir)
        self.downloader = ModelDownloader(models_dir)

        # Estado de modelos cargados
        self.loaded_models = {}
        self.model_paths = {}

        # Configuración de modelos (coherente con tu diseño actual)
        self.intent_model_name = "intent"
        self.conversation_model_name = "conversation"

    async def __aenter__(self):
        """Context manager - mantiene compatibilidad con código actual."""
        try:
            # Asegurar que los modelos estén disponibles
            await self._ensure_models_ready()

            # Cargar modelo de intenciones (siempre activo)
            await self._load_intent_model()

            logger.info("[LLAMACPP] Provider inicializado correctamente")
            return self

        except Exception as e:
            logger.error(f"[LLAMACPP] Error en inicialización: {e}")
            raise LLMError(f"Error inicializando LlamaCpp: {e}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup - mantiene compatibilidad."""
        try:
            # Liberar modelos cargados
            for model_name in list(self.loaded_models.keys()):
                del self.loaded_models[model_name]

            self.loaded_models.clear()

            # Forzar garbage collection
            import gc
            gc.collect()

            logger.info("[LLAMACPP] Provider cerrado correctamente")

        except Exception as e:
            logger.error(f"[LLAMACPP] Error cerrando provider: {e}")

    async def generate_response(
        self,
        prompt: str,
        model_name: str,
        max_tokens: int = 150,
        temperature: float = 0.7
    ) -> LLMResponse:
        """
        Genera respuesta usando modelo especificado.
        Mantiene la misma interfaz que OllamaProvider.
        """
        start_time = time.time()

        try:
            # Mapear nombres de modelos
            internal_model = self._map_model_name(model_name)

            # Cargar modelo si no está en memoria
            if internal_model not in self.loaded_models:
                await self._load_model(internal_model)

            model = self.loaded_models[internal_model]

            logger.debug(f"[LLAMACPP] Generando con {internal_model}: {prompt[:100]}...")

            # Generar respuesta
            response = model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                stop=["User:", "Usuario:", "\n\nUser:", "\n\nUsuario:"],
                echo=False
            )

            generated_text = response["choices"][0]["text"].strip()

            if not generated_text:
                raise LLMError("Modelo devolvió respuesta vacía")

            response_time = time.time() - start_time

            return LLMResponse(
                text=generated_text,
                model=model_name,
                tokens_used=response.get("usage", {}).get("total_tokens", 0),
                response_time=response_time,
                metadata={
                    "finish_reason": response["choices"][0].get("finish_reason"),
                    "internal_model": internal_model
                }
            )

        except Exception as e:
            logger.error(f"[LLAMACPP] Error generando respuesta: {e}")
            raise LLMError(f"Error en generación: {str(e)}")

    async def is_available(self) -> bool:
        """Verifica si el provider está disponible."""
        try:
            # Verificar que llama-cpp-python esté instalado
            import llama_cpp

            # Verificar que el modelo de intenciones esté disponible
            intent_available = "intent" in self.model_paths

            return intent_available

        except ImportError:
            logger.error("[LLAMACPP] llama-cpp-python no está instalado")
            return False
        except Exception as e:
            logger.error(f"[LLAMACPP] Error verificando disponibilidad: {e}")
            return False

    # === MÉTODOS ESPECÍFICOS (mantienen compatibilidad con LLMManager) ===

    async def detect_intent(self, message: str, context: str = "") -> LLMResponse:
        """
        Método específico para detección de intenciones.
        Mantiene compatibilidad con tu LLMManager actual.
        """
        prompt = self._create_intent_prompt(message, context)

        return await self.generate_response(
            prompt=prompt,
            model_name=self.intent_model_name,
            max_tokens=10,  # Respuesta muy corta para intenciones
            temperature=0.1  # Determinística
        )

    async def generate_welcome_message(
        self,
        user_name: str,
        last_conversation: str,
        has_active_flow: bool,
        flow_type: str = "",
        same_day: bool = False
    ) -> LLMResponse:
        """
        Método específico para mensajes de bienvenida.
        Mantiene compatibilidad con tu WelcomeFlowManager.
        """
        time_context = "hoy mismo" if same_day else "hace un tiempo"
        flow_context = f"Tienes un proceso de {flow_type} pendiente. " if has_active_flow else ""

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
            model_name=self.conversation_model_name,
            max_tokens=100,
            temperature=0.8
        )

    # === MÉTODOS PRIVADOS ===

    async def _ensure_models_ready(self):
        """Asegura que todos los modelos estén descargados."""
        for model_name in ["intent", "conversation"]:
            success, model_path = await self.downloader.ensure_model_available(model_name)

            if success:
                self.model_paths[model_name] = model_path
                logger.info(f"[LLAMACPP] Modelo {model_name} listo: {model_path}")
            else:
                raise LLMError(f"No se pudo preparar modelo {model_name}")

    async def _load_model(self, model_name: str):
        """Carga un modelo específico en memoria."""
        try:
            from llama_cpp import Llama

            if model_name not in self.model_paths:
                raise LLMError(f"Modelo {model_name} no está disponible")

            model_path = self.model_paths[model_name]

            logger.info(f"[LLAMACPP] Cargando modelo {model_name}...")

            # Configuración optimizada para tu VPS
            model = Llama(
                model_path=model_path,
                n_ctx=4096 if model_name == "conversation" else 2048,
                n_threads=2,  # Para tu VPS con 2 CPU
                n_gpu_layers=0,  # CPU only para compatibilidad
                use_mmap=True,  # Eficiencia de memoria
                use_mlock=False,  # Evitar bloqueo de memoria
                verbose=False
            )

            self.loaded_models[model_name] = model
            logger.info(f"[LLAMACPP] Modelo {model_name} cargado correctamente")

        except Exception as e:
            logger.error(f"[LLAMACPP] Error cargando modelo {model_name}: {e}")
            raise LLMError(f"Error cargando {model_name}: {e}")

    async def _load_intent_model(self):
        """Carga el modelo de intenciones al inicio."""
        await self._load_model("intent")

    def _map_model_name(self, model_name: str) -> str:
        """Mapea nombres externos a nombres internos."""
        mapping = {
            "tinyllama:1.1b": "intent",
            "mistral:7b-instruct": "conversation",
            # Mantener compatibilidad con tu código actual
            self.intent_model_name: "intent",
            self.conversation_model_name: "conversation"
        }

        return mapping.get(model_name, "conversation")  # Default a conversation

    def _create_intent_prompt(self, message: str, context: str) -> str:
        """Crea prompt optimizado para detección de intenciones."""
        return f"""<|system|>
Eres un clasificador de intenciones para un bot de agendamiento de citas.

INSTRUCCIONES:
- Responde SOLO con UNA palabra
- APPOINTMENT: agendar, cancelar, modificar citas
- FAQ: preguntas sobre servicios, precios, horarios
- SUPPORT: problemas, quejas, errores técnicos
- GREETING: saludos, presentaciones
- END: despedidas, agradecer

<|user|>
Contexto: {context}
Mensaje: "{message}"

Clasificación:<|assistant|>
"""