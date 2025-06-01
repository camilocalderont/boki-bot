import logging
from typing import Optional, Dict
from app.services.external import BokiApi
from app.services.conversation.flows import (BaseFlow, RegistrationFlow, FAQFlow, AppointmentFlow, EndConversationFlow, SupportFlow)
from app.services.conversation.message_processor import MessageProcessor
from app.services.conversation.button_handler import ButtonHandler
from app.services.conversation.flow_router import FlowRouter
from app.services.llm.llm_manager import LLMManager

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Responsabilidad única: Orquestar el procesamiento de conversaciones.
    Coordina los diferentes componentes especializados.
    """

    def __init__(self):
        """
        Inicializa el gestor de conversaciones.
        Configura todos los flujos y componentes necesarios.
        """
        # APIs y recursos
        self.boki_api = BokiApi()

        # Flujos de conversación
        self.flows: Dict[str, BaseFlow] = {
            "registration": RegistrationFlow(),
            "faq": FAQFlow(),
            "appointment": AppointmentFlow(),
            "end_conversation": EndConversationFlow(),
            "support": SupportFlow()
        }

        # Componentes especializados
        self.message_processor = MessageProcessor(self.boki_api)
        self.button_handler = ButtonHandler(self.flows, self.boki_api)
        self.flow_router = FlowRouter(self.flows, self.boki_api)

        # NUEVO: Sistema LLM opcional
        self.llm_system = None  # Se inicializa en _init_llm_system()

    async def _init_llm_system(self):
        """Inicializa sistema LLM de forma segura (no bloquea si falla)"""
        if self.llm_system is not None:
            return  # Ya inicializado

        try:
            self.llm_system = LLMManager(self.boki_api)
            await self.llm_system.initialize()
            logger.info("🧠 Sistema LLM inicializado correctamente")
        except Exception as e:
            logger.warning(f"⚠️ LLM no disponible, usando sistema determinístico: {e}")
            self.llm_system = None

    async def process_message(self, phone_number: str, message_text: str, message_id: Optional[str] = None) -> Optional[str]:
        """
        Procesa un mensaje entrante con estrategia híbrida: LLM + fallback.
        """
        # Intentar inicializar LLM si no se ha hecho (lazy loading)
        await self._init_llm_system()

        # ESTRATEGIA: Probar LLM primero, fallback a sistema determinístico
        if self.llm_system and self.llm_system.is_available():
            # Usar nuevo sistema LLM
            return await self._process_with_llm(phone_number, message_text, message_id)
        else:
            # Tu código actual sin cambios
            return await self._process_original(phone_number, message_text, message_id)

    async def _process_with_llm(self, phone_number: str, message_text: str, message_id: Optional[str] = None) -> Optional[str]:
        """
        Procesamiento mejorado con LLM.
        NUEVO: Usa LLM para detección de intenciones y respuestas naturales.
        """
        try:
            logger.info(f"🧠 Procesando con LLM: {phone_number}")

            # 1. Procesar mensaje entrante (lógica actual)
            message_data = await self.message_processor.process_incoming_message(
                phone_number, message_text, message_id
            )

            # 2. Validar resultado del procesamiento
            if message_data.get("is_duplicate"):
                return None

            if message_data.get("error"):
                return self._get_error_response(message_data["error"])

            # 3. Detectar intención con LLM
            llm_intent = await self.llm_system.detect_intent_with_context(
                message_text, message_data["contact_id"]
            )
            logger.info(f"🎯 LLM detectó intención: {llm_intent.text}")

            # 4. Procesar según tenga flujo activo o no
            if message_data["conversation_state"]:
                # Hay flujo activo - usar lógica determinística pero con respuestas LLM
                response = await self._process_active_flow_with_llm(message_data, llm_intent)
            else:
                # Nuevo flujo - usar LLM para decisión y saludo
                response = await self._process_new_flow_with_llm(message_data, llm_intent)

            # 5. Registrar respuesta
            if response and message_id:
                await self.message_processor.log_outgoing_message(
                    message_data["contact_id"], response
                )

            return response

        except Exception as e:
            logger.error(f"❌ Error en procesamiento LLM: {e}")
            # Fallback automático al sistema original
            return await self._process_original(phone_number, message_text, message_id)

    async def _process_active_flow_with_llm(self, message_data: Dict, llm_intent) -> str:
        """
        Procesa flujo activo con mejoras LLM.
        Ejecuta lógica determinística pero mejora respuestas con LLM.
        """
        try:
            # Ejecutar flujo determinístico normal
            deterministic_response = await self.flow_router.route_message(
                contact_id=message_data["contact_id"],
                phone_number=message_data["phone_number"],
                message_text=message_data["message_text"],
                is_registered=message_data["is_registered"],
                conversation_state=message_data["conversation_state"]
            )

            # Si el flujo devuelve estructura interactiva (botones/listas), no tocar
            if isinstance(deterministic_response, dict):
                return deterministic_response

            # Mejorar respuesta de texto con LLM para hacerla más natural
            enhanced_response = await self._enhance_response_with_llm(
                original_response=deterministic_response,
                user_message=message_data["message_text"],
                conversation_state=message_data["conversation_state"]
            )

            return enhanced_response if enhanced_response else deterministic_response

        except Exception as e:
            logger.error(f"Error en flujo activo con LLM: {e}")
            # Fallback: ejecutar solo lógica determinística
            return await self.flow_router.route_message(
                contact_id=message_data["contact_id"],
                phone_number=message_data["phone_number"],
                message_text=message_data["message_text"],
                is_registered=message_data["is_registered"],
                conversation_state=message_data["conversation_state"]
            )

    async def _process_new_flow_with_llm(self, message_data: Dict, llm_intent) -> str:
        """
        Procesa nuevo flujo con saludo LLM personalizado.
        """
        try:
            # Si usuario no registrado, ir directo a registro
            if not message_data["is_registered"]:
                return await self.flow_router.route_message(
                    contact_id=message_data["contact_id"],
                    phone_number=message_data["phone_number"],
                    message_text=message_data["message_text"],
                    is_registered=False,
                    conversation_state=None
                )

            # Usuario registrado - generar saludo LLM personalizado
            client_data = await self.boki_api.get_client_by_phone(message_data["phone_number"])
            user_name = client_data.get('VcFirstName', 'Usuario') if client_data else 'Usuario'

            # Generar saludo contextual con LLM
            welcome_response = await self.llm_system.generate_welcome_response(
                contact_id=message_data["contact_id"],
                user_name=user_name,
                has_active_flow=False
            )

            # Decidir flujo basado en intención LLM
            flow_decision = self._map_llm_intent_to_flow(llm_intent.text)

            if flow_decision:
                # Combinar saludo LLM + inicio de flujo
                flow_response = await self.flow_router.route_message(
                    contact_id=message_data["contact_id"],
                    phone_number=message_data["phone_number"],
                    message_text=flow_decision,  # Mapear a comando que entiende el flow_router
                    is_registered=True,
                    conversation_state=None
                )

                # Combinar respuestas
                combined_response = f"{welcome_response.text}\n\n{flow_response}"
                return combined_response
            else:
                # Solo saludo LLM + opciones generales
                general_options = "\n\n💬 Puedo ayudarte con:\n• Agendar citas\n• Preguntas frecuentes\n• Soporte técnico"
                return welcome_response.text + general_options

        except Exception as e:
            logger.error(f"Error en nuevo flujo con LLM: {e}")
            # Fallback a lógica determinística
            return await self.flow_router.route_message(
                contact_id=message_data["contact_id"],
                phone_number=message_data["phone_number"],
                message_text=message_data["message_text"],
                is_registered=message_data["is_registered"],
                conversation_state=None
            )

    async def _enhance_response_with_llm(self, original_response: str, user_message: str, conversation_state: Dict) -> Optional[str]:
        """
        Mejora una respuesta determinística con LLM para hacerla más natural.
        """
        try:
            # Solo mejorar respuestas de texto simples
            if len(original_response) > 500 or "●" in original_response or "📋" in original_response:
                return original_response  # No tocar respuestas complejas

            # Crear contexto del flujo
            flow_context = self._extract_flow_context(conversation_state)

            # Generar versión mejorada
            enhanced = await self.llm_system.llm_provider.generate_response(
                prompt=f"""Mejora esta respuesta del sistema para que sea más natural y amigable:

                    Mensaje del usuario: "{user_message}"
                    Respuesta original: "{original_response}"
                    Contexto del flujo: {flow_context}

                    Genera una versión más natural manteniendo la información importante. Máximo 2 líneas:""",
                model_name="conversation",
                max_tokens=100,
                temperature=0.8
            )

            return enhanced.text.strip()

        except Exception as e:
            logger.warning(f"Error mejorando respuesta con LLM: {e}")
            return None

   # === MÉTODOS AUXILIARES ===

    def _map_llm_intent_to_flow(self, llm_intent: str) -> Optional[str]:
        """Mapea intención LLM a comando que entiende el flow_router"""
        intent_mapping = {
            "APPOINTMENT": "agendar",
            "FAQ": "preguntas",
            "SUPPORT": "soporte",
            "GREETING": None,  # No iniciar flujo específico
            "END": "finalizar"
        }
        return intent_mapping.get(llm_intent.upper())

    def _extract_flow_context(self, conversation_state: Optional[Dict]) -> str:
        """Extrae contexto del flujo para LLM"""
        if not conversation_state:
            return "conversación general"

        # CORRECCIÓN: Manejar correctamente la estructura de datos
        if isinstance(conversation_state, dict):
            # Si tiene estructura _doc (de MongoDB), usar esa
            if "_doc" in conversation_state:
                state_data = conversation_state["_doc"]
            else:
                # Si no, usar directamente conversation_state
                state_data = conversation_state

            # Extraer flow y step de forma segura
            flow = state_data.get("flow", "general") if isinstance(state_data, dict) else "general"

            # Para el step, puede estar en state.step o directamente en step
            if isinstance(state_data, dict):
                state_info = state_data.get("state", {})
                if isinstance(state_info, dict):
                    step = state_info.get("step", "inicial")
                else:
                    step = state_data.get("step", "inicial")
            else:
                step = "inicial"

            return f"flujo {flow}, paso {step}"

        return "conversación general"

    def _get_error_response(self, error_type: str) -> str:
        """Retorna respuesta apropiada según el tipo de error."""
        error_responses = {
            "contact_error": "Lo siento, hay un problema técnico. Intenta de nuevo más tarde.",
            "processing_error": "Hubo un error procesando tu mensaje. Por favor intenta de nuevo."
        }
        return error_responses.get(error_type, "Error desconocido. Intenta de nuevo.")

    async def close(self):
        """Cierra recursos del manager."""
        try:
            await self.boki_api.close()
            if self.llm_system:
                await self.llm_system.close()
            logger.debug("Recursos cerrados exitosamente")
        except Exception as e:
            logger.error(f"Error cerrando recursos: {e}")


    async def _process_original(self, phone_number: str, message_text: str, message_id: Optional[str] = None) -> Optional[str]:
        """
        Procesa un mensaje entrante de forma simplificada.
        Responsabilidad única: orquestar el flujo general.
        """
        try:
            logger.info(f"Procesando mensaje de {phone_number}")

            # 1. Procesar mensaje entrante
            message_data = await self.message_processor.process_incoming_message(
                phone_number, message_text, message_id
            )

            # 2. Validar resultado del procesamiento
            if message_data.get("is_duplicate"):
                return None

            if message_data.get("error"):
                return self._get_error_response(message_data["error"])

            # 3. Manejar botones sin estado de conversación
            if (not message_data["conversation_state"] and
                self.button_handler.is_button_id(message_text)):

                response = await self.button_handler.handle_button_without_state(
                    message_data["contact_id"], message_text
                )
            else:
                # 4. Enrutar a flujo apropiado
                response = await self.flow_router.route_message(
                    contact_id=message_data["contact_id"],
                    phone_number=message_data["phone_number"],
                    message_text=message_data["message_text"],
                    is_registered=message_data["is_registered"],
                    conversation_state=message_data["conversation_state"]
                )

            # 5. Registrar respuesta
            if response and message_id:
                await self.message_processor.log_outgoing_message(
                    message_data["contact_id"], response
                )

            return response

        except Exception as e:
            return "Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo."

    def _get_error_response(self, error_type: str) -> str:
        """Retorna respuesta apropiada según el tipo de error."""
        error_responses = {
            "contact_error": "Lo siento, hay un problema técnico. Intenta de nuevo más tarde.",
            "processing_error": "Hubo un error procesando tu mensaje. Por favor intenta de nuevo."
        }
        return error_responses.get(error_type, "Error desconocido. Intenta de nuevo.")

    async def close(self):
        """Cierra recursos del manager."""
        try:
            await self.boki_api.close()
            logger.debug("Recursos cerrados exitosamente")
        except Exception as e:
            logger.error(f"Error cerrando recursos: {e}")