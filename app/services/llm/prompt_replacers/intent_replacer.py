from typing import Dict, Any

class IntentReplacer:
    """Reemplazador simple para prompts de detección de intenciones"""
    
    @staticmethod
    async def replace_variables(prompt_template: str, context: Dict[str, Any]) -> str:
        """Reemplaza variables en el prompt"""
        prompt = prompt_template
        
        # Reemplazo obligatorio
        user_message = context.get('user_message', '')
        prompt = prompt.replace("$[user_message]", user_message)
        
        return prompt 