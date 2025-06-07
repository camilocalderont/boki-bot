import logging
from typing import Optional
from app.services.external import BokiApi
from app.services.external.messages_api import MessagesApi
from app.services.external.contacts_api import ContactsApi
from app.services.llm.llm_service import LLMService
from app.services.conversation.message_processor import MessageProcessor

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Gestor de conversaciones para WhatsApp
    Responsabilidad: Recibir mensaje → Detectar intención → Responder
    """

    def __init__(self):
        """Inicializar servicios básicos"""
        self.boki_api = BokiApi()
        self.messages_api = MessagesApi()
        self.contacts_api = ContactsApi()
        self.llm_service = LLMService(self.boki_api)
        self.message_processor = MessageProcessor(self.boki_api)
        
    async def process_message(self, phone_number: str, message_text: str, message_id: Optional[str] = None) -> Optional[str]:
        """
        Procesa mensaje de WhatsApp:
        1. Valida duplicados
        2. Verifica si el contacto existe
        3. Guarda mensaje entrante
        4. Detecta intención con LLM
        5. Responde según intención
        """
        try:
            
            # PASO 1: Verificar duplicados
            if message_id and await self.message_processor.is_duplicate_message(message_id):
                return None
            
            # PASO 2: Verificar si el contacto existe
            contact_exists = await self.contacts_api.get_contact_by_phone(phone_number)
            
            # PASO 3: Si existe, obtener información del cliente
            client_data = None
            if contact_exists:
                client_data = await self.contacts_api.get_client_by_phone(phone_number)
                
            
            # PASO 4: Determinar contexto de flujo basado en existencia del contacto
            flow_context = {
                "flow": "conversation" if contact_exists else "intent_detection",
                "step": "ongoing_chat" if contact_exists else "initial_contact"
            }
            
            # PASO 5: Guardar mensaje entrante (usando phone como identificador temporal si no existe contacto)
            contact_identifier = phone_number  # Usamos el teléfono como identificador
            await self.messages_api.log_incoming_message(
                contact_id=contact_identifier,
                message_id=message_id or f"incoming_{phone_number}_{hash(message_text)}",
                content=message_text,
                flow_context=flow_context
            )
            
            detected_intent = await self.llm_service.detect_intent(
                user_message=message_text, 
                company_id="1"  # Por ahora fijo
            )
            
            response = self._generate_response(detected_intent, message_text, phone_number)
            return response
            
        except Exception as e:
            logger.error(f"[CONVERSATION] Error procesando mensaje: {e}")
            return "Lo siento, hubo un error. Por favor intenta de nuevo."
    
    def _generate_response(self, intent: str, message: str, phone: str) -> str:
        """Genera respuesta según la intención detectada"""
        
        if intent == "APPOINTMENT":
            return "🗓️ ¡Perfecto! Te ayudo a agendar tu cita.\n\n¿Para qué servicio necesitas la cita?"
            
        elif intent == "FAQ":
            return "❓ Claro, te ayudo con tu consulta.\n\n¿Qué información específica necesitas?"
            
        elif intent == "SUPPORT":
            return "🛠️ Entiendo que tienes un problema.\n\nCuéntame qué está pasando para ayudarte mejor."
            
        elif intent == "GREETING":
            return "👋 ¡Hola! Bienvenido/a.\n\n¿En qué puedo ayudarte hoy?"
            
        elif intent == "END_CONVERSATION":
            return "👋 ¡Gracias por contactarnos!\n\nQue tengas un excelente día. 😊"
            
        else:  # UNKNOWN
            return "🤔 No estoy seguro de entender tu mensaje.\n\n¿Podrías ser más específico sobre lo que necesitas?"
