# app/services/conversation/conversation_manager.py
import logging
import uuid
from typing import Optional, Dict, Any
from app.services.intent_detection.detector import Intent, EnhancedIntentDetector
from app.services.boki_api import BokiApi
from app.services.conversation.flows.registration_flow import RegistrationFlow
from app.services.conversation.flows.faq_flow import FAQFlow
from app.services.conversation.flows.appointment_flow import AppointmentFlow
from app.services.conversation.flows.end_conversation_flow import EndConversationFlow
from app.services.conversation.flows.support_flow import SupportFlow
from app.services.conversation.unknown_handler import UnknownIntentHandler

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Gestiona los flujos de conversación de forma simplificada.
    Responsabilidad única: coordinar flujos basado en estado y intención.
    """

    def __init__(self):
        self.intent_detector = EnhancedIntentDetector()
        self.boki_api = BokiApi()
        self.unknown_handler = UnknownIntentHandler()

        # Inicializar flujos de conversación
        self.flows = {
            "registration": RegistrationFlow(),
            "faq": FAQFlow(),
            "appointment": AppointmentFlow(),
            "end_conversation": EndConversationFlow(),
            "support": SupportFlow()
        }

    async def process_message(self, phone_number: str, message_text: str, message_id: Optional[str] = None) -> Optional[str]:
        """
        Procesa un mensaje entrante de forma simplificada.
        """

        try:
            logger.info(f"[MANAGER] ===== INICIO PROCESAMIENTO =====")
            logger.info(f"[MANAGER] Teléfono: {phone_number}")
            logger.info(f"[MANAGER] Mensaje: {message_text}")
            logger.info(f"[MANAGER] ID: {message_id}")

            # 1. Verificar duplicados
            if message_id and await self.boki_api.is_message_processed(message_id):
                logger.warning(f"[MANAGER] Mensaje {message_id} ya procesado, ignorando")
                return None

            # 2. Obtener/crear contacto
            logger.info(f"[MANAGER] Obteniendo/creando contacto para {phone_number}")
            contact = await self.boki_api.get_or_create_contact(phone_number)

            if not contact or not contact.get("_id"):
                logger.error(f"[MANAGER] No se pudo obtener/crear contacto para {phone_number}")
                logger.error(f"[MANAGER] Respuesta del contacto: {contact}")
                return "Lo siento, hay un problema técnico. Intenta de nuevo más tarde."

            contact_id = contact["_id"]
            logger.info(f"[MANAGER] Contacto obtenido: {contact_id}")

            # 3. Verificar si es usuario registrado
            logger.info(f"[MANAGER] Verificando si usuario está registrado")
            client = await self.boki_api.get_client_by_phone(phone_number)
            is_registered = client is not None
            logger.info(f"[MANAGER] Usuario registrado: {is_registered}")

            # 4. Obtener estado de conversación
            logger.info(f"[MANAGER] Obteniendo estado de conversación")
            conversation_state = await self.boki_api.get_conversation_state(contact_id)
            logger.info(f"[MANAGER] Estado actual: {conversation_state}")

            # 5. Registrar mensaje entrante
            flow_context = self._extract_flow_context(conversation_state)
            logger.info(f"[MANAGER] Contexto de flujo: {flow_context}")

            if message_id:
                logger.info(f"[MANAGER] Registrando mensaje entrante")
                success = await self.boki_api.log_incoming_message(contact_id, message_id, message_text, flow_context)
                logger.info(f"[MANAGER] Mensaje entrante registrado: {success}")

            # 6. Procesar mensaje
            logger.info(f"[MANAGER] Procesando mensaje")
            response = await self._route_message(
                contact_id=contact_id,
                phone_number=phone_number,
                message_text=message_text,
                is_registered=is_registered,
                conversation_state=conversation_state
            )
            logger.info(f"[MANAGER] Respuesta generada: {response[:100]}..." if response else "No hay respuesta")

            # 7. Registrar respuesta
            if response and message_id:
                response_id = f"bot_{uuid.uuid4().hex[:8]}"

                # Obtener contexto actualizado
                updated_state = await self.boki_api.get_conversation_state(contact_id)
                updated_context = self._extract_flow_context(updated_state)

                logger.info(f"[MANAGER] Registrando mensaje saliente")
                success = await self.boki_api.log_outgoing_message(contact_id, response_id, response, updated_context)
                logger.info(f"[MANAGER] Mensaje saliente registrado: {success}")

            logger.info(f"[MANAGER] ===== FIN PROCESAMIENTO =====")
            return response

        except Exception as e:
            logger.error(f"[MANAGER] Error procesando mensaje: {e}", exc_info=True)
            return "Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo."

    def _extract_flow_context(self, conversation_state: Optional[Dict]) -> Dict[str, str]:
        """Extrae el contexto del flujo del estado de conversación."""
        if not conversation_state:
            return {"flow": "general", "step": "initial"}

        # Manejar tanto estructura directa como con _doc
        state_data = conversation_state.get("_doc", conversation_state)
        flow = state_data.get("flow", "general")
        step = state_data.get("state", {}).get("step", "initial")

        return {"flow": flow, "step": step}

    async def _route_message(self, contact_id: str, phone_number: str, message_text: str,
                           is_registered: bool, conversation_state: Optional[Dict]) -> str:
        """Enruta el mensaje al flujo apropiado."""

        # Si hay un flujo activo, continuar con él
        if conversation_state:
            logger.info(f"[MANAGER] Procesando flujo activo")
            return await self._process_active_flow(contact_id, conversation_state, message_text)

        # Si no hay flujo activo, determinar qué hacer
        if is_registered:
            logger.info(f"[MANAGER] Usuario registrado - manejando intención")
            return await self._handle_registered_user(contact_id, phone_number, message_text)
        else:
            logger.info(f"[MANAGER] Usuario no registrado - iniciando registro")
            return await self._start_registration_flow(contact_id, phone_number)

    async def _process_active_flow(self, contact_id: str, conversation_state: Dict, message_text: str) -> str:
        """Procesa un mensaje en un flujo activo."""
        try:
            # Extraer información del estado
            state_data = conversation_state.get("_doc", conversation_state)
            active_flow = state_data.get("flow")
            flow_state = state_data.get("state", {})

            logger.info(f"[MANAGER] Procesando flujo activo '{active_flow}' para contacto {contact_id}")
            logger.info(f"[MANAGER] Estado del flujo: {flow_state}")

            # Obtener el flujo correspondiente
            flow_handler = self.flows.get(active_flow)
            if not flow_handler:
                # Aquí debe llamar al detector de intenciones para saber a que flujo debe ir
                logger.warning(f"[MANAGER] Flujo desconocido: {active_flow}")
                await self.boki_api.clear_conversation_state(contact_id)
                return "Lo siento, algo salió mal. ¿En qué puedo ayudarte?"

            # Procesar mensaje en el flujo
            new_state, response, is_completed = await flow_handler.process_message(
                flow_state, message_text, contact_id
            )

            logger.info(f"[MANAGER] Resultado del flujo - Completado: {is_completed}")
            logger.info(f"[MANAGER] Nuevo estado: {new_state}")

            # Actualizar estado
            if is_completed:
                logger.info(f"[MANAGER] Limpiando estado completado")
                await self.boki_api.clear_conversation_state(contact_id)
                logger.info(f"[MANAGER] Flujo '{active_flow}' completado para contacto {contact_id}")
            elif new_state:
                logger.info(f"[MANAGER] Guardando nuevo estado")
                success = await self.boki_api.save_conversation_state(contact_id, active_flow, new_state)
                logger.info(f"[MANAGER] Estado guardado: {success}")
                if not success:
                    logger.warning(f"[MANAGER] No se pudo guardar estado para contacto {contact_id}")

            return response

        except Exception as e:
            logger.error(f"[MANAGER] Error procesando flujo activo: {e}", exc_info=True)
            await self.boki_api.clear_conversation_state(contact_id)
            return "Hubo un error. ¿En qué puedo ayudarte?"

    async def _handle_registered_user(self, contact_id: str, phone_number: str, message_text: str) -> str:
        """Maneja mensajes de usuarios registrados basado en intención."""
        try:
            intent = self.intent_detector.detect_intent(message_text)
            logger.debug(f"[MANAGER] Intención detectada para usuario registrado: {intent}")

            if intent == Intent.FAQ:
                return await self._start_flow("faq", contact_id, phone_number, message_text)
            elif intent == Intent.APPOINTMENT:
                return await self._start_flow("appointment", contact_id, phone_number, message_text)
            elif intent == Intent.END_CONVERSATION:
                return await self._start_flow("end_conversation", contact_id, phone_number, message_text)
            elif intent == Intent.SUPPORT:
                return await self._start_flow("support", contact_id, phone_number, message_text)
            else:
                # 🎯 Usar el handler inteligente de UNKNOWN
                return self.unknown_handler.handle_unknown_intent(message_text, contact_id)

        except Exception as e:
            logger.error(f"[MANAGER] Error manejando usuario registrado: {e}")
            return "¿En qué puedo ayudarte?"

    async def _start_registration_flow(self, contact_id: str, phone_number: str) -> str:
        """Inicia el flujo de registro para usuarios no registrados."""
        try:
            initial_state = {"step": "waiting_id", "data": {"phone": phone_number}}

            logger.info(f"[MANAGER] Iniciando flujo de registro con estado: {initial_state}")

            success = await self.boki_api.save_conversation_state(contact_id, "registration", initial_state)

            logger.info(f"[MANAGER] Estado de registro guardado: {success}")

            if not success:
                logger.error(f"[MANAGER] No se pudo iniciar flujo de registro para {contact_id}")
                return "Hay un problema técnico. Intenta de nuevo más tarde."

            logger.info(f"[MANAGER] Flujo de registro iniciado para contacto {contact_id}")

            return (
                "¡Hola! 👋 Parece que eres nuevo aquí.\n\n"
                "Para poder ayudarte mejor, necesito que te registres.\n\n"
                "Por favor, proporciona tu número de documento de identidad:"
            )

        except Exception as e:
            logger.error(f"[MANAGER] Error iniciando flujo de registro: {e}", exc_info=True)
            return "Hubo un error. Intenta de nuevo más tarde."

    async def _start_flow(self, flow_name: str, contact_id: str, phone_number: str, message_text: str) -> str:
        """Inicia un flujo específico."""
        try:
            flow_handler = self.flows.get(flow_name)
            if not flow_handler:
                logger.error(f"[MANAGER] Flujo no encontrado: {flow_name}")
                return "Lo siento, no puedo procesar esa solicitud ahora."

            # Procesar mensaje inicial en el flujo
            new_state, response, is_completed = await flow_handler.process_message(
                {}, message_text, contact_id
            )

            # Guardar estado si el flujo no se completó inmediatamente
            if not is_completed and new_state:
                success = await self.boki_api.save_conversation_state(contact_id, flow_name, new_state)
                if not success:
                    logger.warning(f"[MANAGER] No se pudo guardar estado inicial para flujo {flow_name}")

            logger.info(f"[MANAGER] Flujo '{flow_name}' iniciado para contacto {contact_id}")
            return response

        except Exception as e:
            logger.error(f"[MANAGER] Error iniciando flujo {flow_name}: {e}")
            return "Hubo un error procesando tu solicitud."

    async def close(self):
        """Cierra recursos del manager."""
        try:
            await self.boki_api.close()
            logger.debug("[MANAGER] Recursos cerrados")
        except Exception as e:
            logger.error(f"[MANAGER] Error cerrando recursos: {e}")