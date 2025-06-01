from typing import Optional
#from .ollama_provider import OllamaProvider
from .llamacpp_provider import LlamaCppProvider
from .message_history import MessageHistory
from .base_llm import LLMResponse, LLMError
import logging

logger = logging.getLogger(__name__)

class LLMManager:
    """
    Coordinador de LLMs para tu flujo específico.
    """

    def __init__(self, boki_api):
        self.boki_api = boki_api
        self.llm_provider = None
        self.message_history = MessageHistory(boki_api)

    async def initialize(self):
        """Inicializa conexión con Ollama."""
        try:
            self.llm_provider = LlamaCppProvider()
            await self.llm_provider.__aenter__()

            # Verificar que los modelos estén disponibles
            if not await self.llm_provider.is_available():
                raise LLMError("Provider no está disponible")

            logger.info("[LLM_MANAGER] Inicializado exitosamente")

        except Exception as e:
            logger.error(f"[LLM_MANAGER] Error en inicialización: {e}")
            raise

    async def detect_intent_with_context(
        self,
        message: str,
        contact_id: str
    ) -> LLMResponse:
        """
        Detecta intención usando TinyLlama con contexto de historial.
        """
        try:
            # Obtener contexto del historial
            recent_messages = await self.message_history.get_recent_messages(contact_id, 5)
            context = self.message_history.format_conversation_context(recent_messages)

            logger.debug(f"[LLM_MANAGER] Detectando intención para: {message[:50]}...")

            # Detectar intención con TinyLlama
            response = await self.llm_provider.detect_intent(message, context)

            logger.info(f"[LLM_MANAGER] Intención detectada: {response.text}")

            return response

        except Exception as e:
            logger.error(f"[LLM_MANAGER] Error detectando intención: {e}")
            # Fallback: crear respuesta manual
            return LLMResponse(
                text="GENERAL",
                model="fallback",
                tokens_used=0,
                response_time=0.0
            )

    async def generate_welcome_response(
        self,
        contact_id: str,
        user_name: str,
        has_active_flow: bool = False,
        flow_type: str = ""
    ) -> LLMResponse:
        """
        Genera mensaje de bienvenida personalizado usando Mistral.
        """
        try:
            # Obtener historial completo
            recent_messages = await self.message_history.get_recent_messages(contact_id, 10)

            # Determinar contexto temporal
            same_day = self.message_history.was_conversation_today(recent_messages)

            # Crear resumen de la última conversación
            last_conversation = self.message_history.get_last_conversation_summary(recent_messages)

            logger.debug(f"[LLM_MANAGER] Generando bienvenida para {user_name}, same_day: {same_day}")

            # Generar saludo con Mistral
            response = await self.llm_provider.generate_welcome_message(
                user_name=user_name,
                last_conversation=last_conversation,
                has_active_flow=has_active_flow,
                flow_type=flow_type,
                same_day=same_day
            )

            logger.info(f"[LLM_MANAGER] Bienvenida generada para {user_name}")

            return response

        except Exception as e:
            logger.error(f"[LLM_MANAGER] Error generando bienvenida: {e}")
            # Fallback: saludo genérico
            fallback_text = f"¡Hola {user_name}! ¿En qué puedo ayudarte hoy?"
            return LLMResponse(
                text=fallback_text,
                model="fallback",
                tokens_used=0,
                response_time=0.0
            )

    async def decide_flow_routing(
        self,
        message: str,
        contact_id: str,
        available_flows: list
    ) -> LLMResponse:
        """
        Decide a qué flujo enviar al usuario usando Mistral.
        """
        try:
            # Obtener contexto
            recent_messages = await self.message_history.get_recent_messages(contact_id, 3)
            context = self.message_history.format_conversation_context(recent_messages)

            # Crear prompt para decisión de flujo
            flows_text = ", ".join(available_flows)

            prompt = f"""Eres un asistente de una clínica de belleza. Basándote en el mensaje del usuario, decide a qué flujo enviarlo.

Contexto de conversación reciente:
{context}

Mensaje actual del usuario: "{message}"

Flujos disponibles: {flows_text}

Responde SOLO con el nombre del flujo más apropiado, o "general" si no hay uno específico.

Flujo recomendado:"""

            response = await self.llm_provider.generate_response(
                prompt=prompt,
                model_name=self.llm_provider.conversation_model,
                max_tokens=20,
                temperature=0.3  # Baja temperatura para decisión
            )

            logger.info(f"[LLM_MANAGER] Flujo recomendado: {response.text}")

            return response

        except Exception as e:
            logger.error(f"[LLM_MANAGER] Error decidiendo flujo: {e}")
            return LLMResponse(
                text="general",
                model="fallback",
                tokens_used=0,
                response_time=0.0
            )

    async def should_continue_flow(
        self,
        contact_id: str,
        flow_type: str,
        flow_data: dict
    ) -> LLMResponse:
        """
        Decide si el usuario quiere continuar un flujo pendiente.
        """
        try:
            # Obtener contexto del historial
            recent_messages = await self.message_history.get_recent_messages(contact_id, 5)
            context = self.message_history.format_conversation_context(recent_messages)

            # Resumir el estado del flujo
            flow_summary = self._summarize_flow_state(flow_type, flow_data)

            prompt = f"""Analiza si el usuario quiere continuar con su proceso pendiente.

Contexto de conversación:
{context}

Proceso pendiente: {flow_type}
Estado actual: {flow_summary}

Último mensaje del usuario: "{recent_messages[-1]['content'] if recent_messages else ''}"

¿El usuario quiere continuar con el proceso pendiente?
Responde SOLO: "SI" o "NO"

Respuesta:"""

            response = await self.llm_provider.generate_response(
                prompt=prompt,
                model_name=self.llm_provider.conversation_model,
                max_tokens=5,
                temperature=0.2
            )

            logger.info(f"[LLM_MANAGER] ¿Continuar flujo? {response.text}")

            return response

        except Exception as e:
            logger.error(f"[LLM_MANAGER] Error evaluando continuación: {e}")
            return LLMResponse(
                text="NO",
                model="fallback",
                tokens_used=0,
                response_time=0.0
            )

    def _summarize_flow_state(self, flow_type: str, flow_data: dict) -> str:
        """
        Crea un resumen del estado actual del flujo.
        """
        if flow_type == "appointment":
            step = flow_data.get("step", "inicial")
            if step == "waiting_category":
                return "Seleccionando categoría de servicio"
            elif step == "waiting_service":
                return "Seleccionando servicio específico"
            elif step == "waiting_professional":
                return "Seleccionando profesional"
            elif step == "waiting_date":
                return "Seleccionando fecha"
            elif step == "waiting_time":
                return "Seleccionando horario"
            elif step == "waiting_confirmation":
                return "Confirmando cita"
            else:
                return f"En proceso de agendamiento (paso: {step})"

        elif flow_type == "registration":
            step = flow_data.get("step", "inicial")
            if step == "waiting_id":
                return "Registrando documento de identidad"
            elif step == "waiting_name":
                return "Registrando nombre"
            else:
                return f"En proceso de registro (paso: {step})"

        else:
            return f"En proceso de {flow_type}"

    async def get_conversation_insights(self, contact_id: str) -> dict:
        """
        Obtiene insights de la conversación para debugging/analytics.
        """
        try:
            messages = await self.message_history.get_recent_messages(contact_id, 20)
            stats = self.message_history.get_conversation_stats(messages)

            # Detectar temas frecuentes
            appointment_keywords = ["cita", "agendar", "turno", "reserva"]
            has_appointment_history = self.message_history.has_keywords_in_history(
                messages, appointment_keywords
            )

            return {
                "stats": stats,
                "has_appointment_history": has_appointment_history,
                "last_conversation_today": self.message_history.was_conversation_today(messages),
                "conversation_summary": self.message_history.get_last_conversation_summary(messages)
            }

        except Exception as e:
            logger.error(f"[LLM_MANAGER] Error obteniendo insights: {e}")
            return {}

    async def close(self):
        """Cierra recursos."""
        try:
            if self.llm_provider:
                await self.llm_provider.__aexit__(None, None, None)
            logger.info("[LLM_MANAGER] Recursos cerrados")
        except Exception as e:
            logger.error(f"[LLM_MANAGER] Error cerrando recursos: {e}")

    def is_available(self) -> bool:
        """Verifica si el sistema LLM está disponible."""
        return self.llm_provider is not None and self.llm_provider.is_available()
