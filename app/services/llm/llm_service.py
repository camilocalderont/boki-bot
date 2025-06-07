import logging
from .agents.intent_agent import IntentAgent

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, llm_api_service):
        self.llm_api = llm_api_service
    
    async def detect_intent(self, user_message: str, company_id: str) -> str:
        agent = IntentAgent(self.llm_api)
        return await agent.detect_intent(user_message, company_id)
    
    async def process_appointment(self, user_message: str, company_id: str, 
                                context: dict = None) -> dict:
        # TODO: Implementar AppointmentAgent
        raise NotImplementedError("AppointmentAgent pendiente de implementar")
    
    async def answer_faq(self, user_message: str, company_id: str) -> str:
        # TODO: Implementar FAQAgent  
        raise NotImplementedError("FAQAgent pendiente de implementar")
    
    async def handle_support(self, user_message: str, company_id: str) -> str:
        # TODO: Implementar SupportAgent
        raise NotImplementedError("SupportAgent pendiente de implementar")
    
    async def process_message(self, user_message: str, company_id: str, 
                            context: dict = None) -> dict:
        """
        Procesa cualquier mensaje detectando primero la intención
        """
        intent = await self.detect_intent(user_message, company_id)
        
        result = {
            "intent": intent,
            "response": None,
            "data": None
        }
        
        if intent == "APPOINTMENT":
            result["data"] = await self.process_appointment(user_message, company_id, context)
        elif intent == "FAQ":
            result["response"] = await self.answer_faq(user_message, company_id)
        elif intent == "SUPPORT":
            result["response"] = await self.handle_support(user_message, company_id)
        elif intent == "END_CONVERSATION":
            result["response"] = "¡Gracias por contactarnos!"
        else:
            result["response"] = "No entendí tu mensaje. ¿Podrías ser más específico?"
        
        return result