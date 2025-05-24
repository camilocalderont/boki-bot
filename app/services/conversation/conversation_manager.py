import logging
import uuid
from app.services.intent_detection.detector import Intent, IntentDetector
from app.services.boki_api import BokiApi
from app.services.conversation.flows.registration_flow import RegistrationFlow
from app.services.conversation.flows.faq_flow import FAQFlow
from app.services.conversation.flows.appointment_flow import AppointmentFlow
from app.services.conversation.flows.end_conversation_flow import EndConversationFlow

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Gestiona los flujos de conversación según la intención detectada
    y el estado del usuario (registrado o no).
    """

    def __init__(self):
        self.intent_detector = IntentDetector()
        self.boki_api = BokiApi()

        # Inicializar flujos de conversación
        self.registration_flow = RegistrationFlow()
        self.faq_flow = FAQFlow()
        self.appointment_flow = AppointmentFlow()
        self.end_conversation_flow = EndConversationFlow()

    async def process_message(self, phone_number: str, message_text: str, message_id: str = None):
        """
        Procesa un mensaje entrante y determina qué flujo debe seguir.

        Args:
            phone_number: Número de teléfono del remitente.
            message_text: Texto del mensaje.
            message_id: ID único del mensaje de WhatsApp.

        Returns:
            str: La respuesta que se enviará al usuario.
        """
        
        # 🆕 1. Verificar si ya procesamos este mensaje (evitar duplicados)
        already_processed = await self.boki_api.is_message_processed(message_id)
        if already_processed:
            return None
        
        # 🆕 2. Buscar cliente en PostgreSQL
        client_found = await self.boki_api.get_client_by_phone(phone_number)
        
        # 🆕 3. Obtener/crear contacto en MongoDB
        contact = await self.boki_api.get_or_create_contact(phone_number)
        contact_id = contact.get("_id")
        
        # 🔧 4. SOLO usar MongoDB como fuente de verdad - NO cache
        conversation_state = await self.boki_api.get_conversation_state(contact_id)

        # Determinar contexto del flujo para logging
        flow_context = None
        if conversation_state:
            # El estado viene de MongoDB con estructura _doc
            doc_data = conversation_state.get("_doc", conversation_state)
            flow_context = {
                "flow": doc_data.get("flow"),
                "step": doc_data.get("state", {}).get("step")
            }

        # 🆕 5. Registrar mensaje entrante
        if message_id:
            await self.boki_api.log_incoming_message(contact_id, message_id, message_text, flow_context)

        # 6. Procesar mensaje según el estado actual
        response = None

        # 🆕 Verificar si hay un flujo activo a través del API (no en memoria)
        if conversation_state:
            response = await self._process_active_flow(
                contact_id, phone_number, message_text, conversation_state
            )
        else:
            # Nueva interacción
            response = await self._handle_new_interaction(contact_id, phone_number, message_text)

        # 🆕 7. Registrar mensaje saliente
        if response and message_id:
            response_id = f"bot_{uuid.uuid4().hex[:8]}"
            # Obtener el estado más reciente para el contexto
            final_context = None
            current_state = await self.boki_api.get_conversation_state(contact_id)
            if current_state:
                doc_data = current_state.get("_doc", current_state)
                final_context = {
                    "flow": doc_data.get("flow"),
                    "step": doc_data.get("state", {}).get("step")
                }
            
            await self.boki_api.log_outgoing_message(contact_id, response_id, response, final_context)

        return response

    async def _process_active_flow(self, contact_id: str, phone_number: str, message_text: str, conversation_state: dict):
        """Procesa un mensaje en un flujo activo."""
        # El estado viene de MongoDB con estructura _doc
        doc_data = conversation_state.get("_doc", conversation_state)
        active_flow = doc_data.get("flow")
        flow_state = doc_data.get("state", {})
        
        # 🆕 NUEVA LÓGICA - usar estructura tupla (state, response, completed)
        response = None
        new_state = None
        flow_completed = False
        
        if active_flow == "registration":
            new_state, response, flow_completed = await self.registration_flow.process_message(
                flow_state, message_text, contact_id
            )
        elif active_flow == "faq":
            new_state, response, flow_completed = await self.faq_flow.process_message(
                flow_state, message_text, contact_id
            )
        elif active_flow == "appointment":
            new_state, response, flow_completed = await self.appointment_flow.process_message(
                flow_state, message_text, contact_id
            )
        elif active_flow == "end_conversation":
            new_state, response, flow_completed = await self.end_conversation_flow.process_message(
                flow_state, message_text, contact_id
            )
        else:
            logger.warning(f"[FLUJO] Flujo no reconocido: {active_flow}")
            response = "Lo siento, algo salió mal. ¿Puedes intentar de nuevo?"
            new_state = None
            flow_completed = True
        
        # 🆕 Actualizar estado a través del API (no en memoria)
        if flow_completed:
            await self.boki_api.clear_conversation_state(contact_id)
        elif new_state:
            await self.boki_api.upsert_conversation_state(contact_id, active_flow, new_state)

        return response

    async def _handle_new_interaction(self, contact_id: str, phone_number: str, message_text: str):
        """Maneja una nueva interacción, verificando si el usuario está registrado."""
        # Verificar si el usuario está registrado
        client = await self.boki_api.get_client_by_phone(phone_number)

        if client:
            # Usuario registrado, detectar intención
            return await self._handle_registered_user(contact_id, phone_number, message_text)
        else:
            # Usuario no registrado, iniciar flujo de registro
            return await self._start_registration_flow(contact_id, phone_number)

    async def _handle_registered_user(self, contact_id: str, phone_number: str, message_text: str):
        """Maneja el mensaje de un usuario registrado basado en la intención."""
        intent = self.intent_detector.detect_intent(message_text)

        if intent == Intent.FAQ:
            return await self._start_faq_flow(contact_id, phone_number, message_text)
        elif intent == Intent.APPOINTMENT:
            return await self._start_appointment_flow(contact_id, phone_number, message_text)
        elif intent == Intent.END_CONVERSATION:
            return await self._start_end_conversation_flow(contact_id, phone_number, message_text)
        else:
            # Intención desconocida, mensaje genérico
            return ("No entendí lo que necesitas. ¿Quieres hacer una pregunta, "
                   "agendar una cita o finalizar la conversación?")

    async def _start_registration_flow(self, contact_id: str, phone_number: str):
        """Inicia el flujo de registro para un usuario no registrado."""
        
        # 🆕 Guardar estado a través del API (no en memoria)
        initial_state = {"step": "waiting_id", "data": {"phone": phone_number}}
        
        result = await self.boki_api.upsert_conversation_state(contact_id, "registration", initial_state)
        
        # Verificación adicional: comprobar si el estado se guardó correctamente
        saved_state = await self.boki_api.get_conversation_state(contact_id)
        
        # Si no se pudo guardar el estado, intentar una vez más
        if not saved_state:
            logger.warning(f"[FLUJO] No se pudo guardar el estado, reintentando")
            await self.boki_api.upsert_conversation_state(contact_id, "registration", initial_state)
            saved_state = await self.boki_api.get_conversation_state(contact_id)

        return ("Parece que no estás registrado en nuestro sistema. "
               "Por favor, proporciona tu número de documento de identidad:")

    async def _start_faq_flow(self, contact_id: str, phone_number: str, message_text: str):
        """Inicia el flujo de preguntas frecuentes."""
        response, state, completed = await self.faq_flow.process_message(
            contact_id, phone_number, message_text, {}
        )

        # 🆕 Guardar estado a través del API si el flujo no ha terminado
        if not completed and state:
            await self.boki_api.upsert_conversation_state(contact_id, "faq", state)

        return response

    async def _start_appointment_flow(self, contact_id: str, phone_number: str, message_text: str):
        """Inicia el flujo de agendamiento de citas."""
        response, state, completed = await self.appointment_flow.process_message(
            contact_id, phone_number, message_text, {}
        )

        # 🆕 Guardar estado a través del API si el flujo no ha terminado
        if not completed and state:
            await self.boki_api.upsert_conversation_state(contact_id, "appointment", state)

        return response

    async def _start_end_conversation_flow(self, contact_id: str, phone_number: str, message_text: str):
        """Inicia el flujo de fin de conversación."""
        response, _, _ = await self.end_conversation_flow.process_message(
            contact_id, phone_number, message_text, {}
        )

        return response
