# ================================
# app/services/llm/welcome_flow.py
# ================================
"""
Flujo de bienvenida inteligente que integra con el sistema existente.
"""

import logging
from typing import Optional, Dict, Tuple
from app.services.external import BokiApi
from .llm_manager import LLMManager

logger = logging.getLogger(__name__)

class WelcomeFlowManager:
    """
    Maneja el flujo de bienvenida inteligente que describiste:
    1. Usuario registrado envía mensaje
    2. Bot consulta historial y genera saludo contextual
    3. Detecta si quiere continuar flujo o empezar nuevo
    """

    def __init__(self):
        self.boki_api = BokiApi()
        self.llm_manager = LLMManager(self.boki_api)
        self.initialized = False

    async def initialize(self):
        """Inicializa el sistema LLM."""
        if not self.initialized:
            await self.llm_manager.initialize()
            self.initialized = True
            logger.info("[WELCOME_FLOW] Inicializado")

    async def process_welcome_message(
        self, 
        contact_id: str, 
        phone_number: str, 
        message: str
    ) -> Tuple[str, Optional[str], Optional[Dict]]:
        """
        Procesa mensaje de usuario registrado y decide el flujo.
        
        Returns:
            Tuple[respuesta, flujo_sugerido, datos_flujo]
        """
        try:
            # Asegurar inicialización
            await self.initialize()
            
            # Obtener información del usuario
            client_data = await self.boki_api.get_client_by_phone(phone_number)
            if not client_data:
                return "Error obteniendo datos del usuario", None, None
            
            user_name = client_data.get('VcFirstName', 'Usuario')
            
            # Verificar si hay flujo activo
            conversation_state = await self.boki_api.get_conversation_state(contact_id)
            has_active_flow = conversation_state is not None
            
            flow_type = ""
            flow_data = {}
            if has_active_flow:
                state_data = conversation_state.get("_doc", conversation_state)
                flow_type = state_data.get("flow", "")
                flow_data = state_data.get("state", {})
            
            # Detectar intención del mensaje
            intent_response = await self.llm_manager.detect_intent_with_context(
                message, contact_id
            )
            detected_intent = intent_response.text.strip().upper()
            
            logger.info(f"[WELCOME_FLOW] Usuario: {user_name}, Intención: {detected_intent}, Flujo activo: {has_active_flow}")
            
            # Procesar según la intención y estado
            if has_active_flow and detected_intent == "CONTINUE_FLOW":
                return await self._handle_continue_flow(contact_id, user_name, flow_type, flow_data)
            
            elif has_active_flow:
                return await self._handle_active_flow_with_new_intent(
                    contact_id, user_name, flow_type, flow_data, detected_intent
                )
            
            else:
                return await self._handle_new_conversation(
                    contact_id, user_name, detected_intent
                )
        
        except Exception as e:
            logger.error(f"[WELCOME_FLOW] Error procesando mensaje: {e}")
            return "¡Hola! ¿En qué puedo ayudarte hoy?", None, None

    async def _handle_continue_flow(
        self, 
        contact_id: str, 
        user_name: str, 
        flow_type: str, 
        flow_data: Dict
    ) -> Tuple[str, str, Dict]:
        """Maneja cuando el usuario quiere continuar un flujo activo."""
        
        # Generar mensaje de continuación
        welcome_response = await self.llm_manager.generate_welcome_response(
            contact_id=contact_id,
            user_name=user_name,
            has_active_flow=True,
            flow_type=flow_type
        )
        
        # Agregar instrucciones específicas
        response_text = welcome_response.text + "\n\n¿Quieres continuar donde lo dejamos?"
        
        return response_text, flow_type, flow_data

    async def _handle_active_flow_with_new_intent(
        self,
        contact_id: str,
        user_name: str,
        flow_type: str,
        flow_data: Dict,
        new_intent: str
    ) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Maneja cuando hay flujo activo pero el usuario tiene nueva intención."""
        
        # Preguntar si quiere continuar o cambiar
        should_continue = await self.llm_manager.should_continue_flow(
            contact_id, flow_type, flow_data
        )
        
        if should_continue.text.strip().upper() == "SI":
            return await self._handle_continue_flow(contact_id, user_name, flow_type, flow_data)
        else:
            # Limpiar flujo activo y procesar nueva intención
            await self.boki_api.clear_conversation_state(contact_id)
            return await self._handle_new_conversation(contact_id, user_name, new_intent)

    async def _handle_new_conversation(
        self,
        contact_id: str,
        user_name: str,
        intent: str
    ) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Maneja nueva conversación sin flujo activo."""
        
        # Generar saludo personalizado
        welcome_response = await self.llm_manager.generate_welcome_response(
            contact_id=contact_id,
            user_name=user_name,
            has_active_flow=False
        )
        
        # Decidir flujo según intención
        if intent == "APPOINTMENT":
            return welcome_response.text + "\n\n¡Perfecto! Te ayudo a agendar tu cita.", "appointment", {}
        
        elif intent == "FAQ":
            return welcome_response.text + "\n\n¡Claro! ¿Qué información necesitas?", "faq", {}
        
        elif intent == "SUPPORT":
            return welcome_response.text + "\n\nEntiendo que tienes un problema. Cuéntame qué pasó.", "support", {}
        
        else:  # GENERAL o desconocido
            # Usar LLM para decidir flujo
            flow_decision = await self.llm_manager.decide_flow_routing(
                message=f"Último mensaje del usuario: {intent}",
                contact_id=contact_id,
                available_flows=["appointment", "faq", "support"]
            )
            
            suggested_flow = flow_decision.text.strip().lower()
            if suggested_flow in ["appointment", "faq", "support"]:
                return welcome_response.text, suggested_flow, {}
            else:
                return welcome_response.text, None, None

    async def close(self):
        """Cierra recursos."""
        await self.llm_manager.close()
        await self.boki_api.close()