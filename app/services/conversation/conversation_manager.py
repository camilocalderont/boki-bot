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
            # Verificar si el mensaje parece ser un ID de botón de un flujo activo
            if self._is_button_id(message_text):
                logger.info(f"[MANAGER] Detectado posible ID de botón: {message_text}")
                return await self._handle_button_without_state(contact_id, message_text)
            
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

    def _is_button_id(self, message: str) -> bool:
        """Detecta si un mensaje parece ser un ID de botón."""
        # Patrones comunes de IDs de botones
        button_patterns = [
            r'^cat_id_\d+$',      # cat_id_1, cat_id_2, etc.
            r'^srv_id_\d+$',      # srv_id_1, srv_id_2, etc.
            r'^prof_id_\d+$',     # prof_id_1, prof_id_2, etc.
            r'^date_\d+$',        # date_1, date_2, etc.
            r'^time_\d+$',        # time_1, time_2, etc.
            r'^confirm_(yes|no)$', # confirm_yes, confirm_no
            r'^date_more$',       # date_more
            r'^date_back$',       # date_back
        ]
        
        import re
        for pattern in button_patterns:
            if re.match(pattern, message.strip()):
                return True
        return False

    async def _handle_button_without_state(self, contact_id: str, button_id: str) -> str:
        """Maneja un ID de botón cuando no hay estado de conversación guardado."""
        try:
            logger.info(f"[MANAGER] Manejando botón sin estado: {button_id}")
            
            # Determinar el tipo de botón y el flujo apropiado
            if button_id.startswith('cat_id_'):
                # Es una selección de categoría - podemos reconstruir el contexto
                logger.info(f"[MANAGER] Detectado botón de categoría, reconstruyendo contexto")
                
                # Extraer el ID de la categoría del botón
                try:
                    category_id = int(button_id.replace('cat_id_', ''))
                    logger.info(f"[MANAGER] ID de categoría extraído: {category_id}")
                    
                    # Iniciar flujo de appointment y procesar la selección de categoría
                    flow_handler = self.flows.get("appointment")
                    if flow_handler:
                        # Simular el estado inicial del flujo
                        initial_state, initial_response, _ = await flow_handler.process_message({}, "agendar", contact_id)
                        
                        if initial_state and initial_state.get("step") == "waiting_category":
                            # Ahora procesar la selección de categoría
                            new_state, response, is_completed = await flow_handler.process_message(
                                initial_state, button_id, contact_id
                            )
                            
                            # Guardar el nuevo estado si no se completó
                            if not is_completed and new_state:
                                success = await self.boki_api.save_conversation_state(contact_id, "appointment", new_state)
                                logger.info(f"[MANAGER] Estado reconstruido guardado: {success}")
                            
                            return response
                        
                except (ValueError, Exception) as e:
                    logger.error(f"[MANAGER] Error reconstruyendo contexto de categoría: {e}")
                
                # Si falla la reconstrucción, reiniciar flujo
                return await self._start_flow("appointment", contact_id, "", "agendar")
            
            elif button_id.startswith('srv_id_'):
                # Es una selección de servicio - más complejo de reconstruir
                logger.info(f"[MANAGER] Detectado botón de servicio sin contexto")
                return ("Lo siento, parece que se perdió el contexto de la conversación. "
                       "Por favor, vuelve a iniciar el proceso escribiendo 'agendar'.")
            
            elif button_id.startswith('prof_id_'):
                # Es una selección de profesional
                logger.info(f"[MANAGER] Detectado botón de profesional sin contexto")
                return ("Lo siento, parece que se perdió el contexto de la conversación. "
                       "Por favor, vuelve a iniciar el proceso escribiendo 'agendar'.")
            
            elif button_id.startswith(('date_', 'time_', 'confirm_')):
                # Son pasos avanzados del flujo
                logger.info(f"[MANAGER] Detectado botón de paso avanzado sin contexto")
                return ("Lo siento, parece que se perdió el contexto de la conversación. "
                       "Por favor, vuelve a iniciar el proceso escribiendo 'agendar'.")
            
            else:
                # ID de botón no reconocido
                logger.warning(f"[MANAGER] ID de botón no reconocido: {button_id}")
                return self.unknown_handler.handle_unknown_intent(button_id, contact_id)
                
        except Exception as e:
            logger.error(f"[MANAGER] Error manejando botón sin estado: {e}")
            return "Hubo un error. Por favor, intenta nuevamente."

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

            # Intentar guardar estado si el flujo no se completó inmediatamente
            if not is_completed and new_state:
                success = await self.boki_api.save_conversation_state(contact_id, flow_name, new_state)
                if not success:
                    logger.warning(f"[MANAGER] No se pudo guardar estado inicial para flujo {flow_name}")
                    # Continuar sin guardar estado - el flujo puede funcionar sin persistencia
                else:
                    logger.info(f"[MANAGER] Estado guardado exitosamente para flujo {flow_name}")

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