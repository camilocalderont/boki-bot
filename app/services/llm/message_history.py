from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MessageHistory:
    """
    Maneja el historial de mensajes para contexto LLM.
    """

    def __init__(self, boki_api):
        self.boki_api = boki_api

    async def get_recent_messages(
        self, 
        contact_id: str, 
        limit: int = 20
    ) -> List[Dict]:
        """
        Obtiene los últimos N mensajes de un contacto.
        
        Returns:
            Lista de mensajes con formato:
            [
                {
                    "role": "user" | "assistant",
                    "content": "texto del mensaje",
                    "timestamp": datetime,
                    "message_id": "id"
                }
            ]
        """
        try:
            # Aquí deberías hacer la consulta real a tu API
            # Por ahora simulo la estructura que necesitas
            
            # TODO: Implementar consulta real a message-history
            # Ejemplo de lo que deberías obtener:
            messages = await self._fetch_messages_from_api(contact_id, limit)
            
            # Formatear para LLM
            formatted_messages = []
            for msg in messages:
                formatted_messages.append({
                    "role": "user" if msg.get("direction") == "inbound" else "assistant",
                    "content": msg.get("content", {}).get("text", ""),
                    "timestamp": msg.get("timestamp"),
                    "message_id": msg.get("messageId")
                })
            
            return formatted_messages[-limit:]  # Últimos N mensajes
            
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            return []

    async def _fetch_messages_from_api(self, contact_id: str, limit: int) -> List[Dict]:
        """
        Consulta real a la API de message-history.
        """
        try:
            # TODO: Implementar consulta real
            # Esta sería la consulta real a tu API cuando esté lista:
            # url = f"message-history/contact/{contact_id}?limit={limit}&sort=-timestamp"
            # response = await self.boki_api._make_request("GET", url)
            
            # Por ahora retorna lista vacía
            # Cuando implementes la API real, descomenta estas líneas:
            
            # if response.status_code == 200:
            #     data = response.json()
            #     return data.get("data", [])
            # else:
            #     logger.warning(f"API devolvió status {response.status_code}")
            #     return []
            
            return []
            
        except Exception as e:
            logger.error(f"Error consultando API: {e}")
            return []

    def format_conversation_context(self, messages: List[Dict]) -> str:
        """
        Formatea el historial para usar como contexto en prompts.
        """
        if not messages:
            return "Sin conversaciones previas."
        
        context_lines = []
        for msg in messages[-5:]:  # Últimos 5 mensajes para contexto
            role = "Usuario" if msg["role"] == "user" else "Bot"
            content = msg["content"][:100]  # Truncar mensajes largos
            if content.strip():  # Solo agregar si hay contenido
                context_lines.append(f"{role}: {content}")
        
        return "\n".join(context_lines) if context_lines else "Sin conversaciones previas."

    def was_conversation_today(self, messages: List[Dict]) -> bool:
        """
        Verifica si hubo conversación hoy.
        """
        if not messages:
            return False
        
        try:
            today = datetime.now().date()
            last_message = messages[-1]
            
            # TODO: Parsear timestamp correctamente según formato de tu API
            # Esto depende del formato que use tu API para timestamps
            # Ejemplos comunes:
            # last_date = datetime.fromisoformat(last_message["timestamp"]).date()
            # last_date = datetime.strptime(last_message["timestamp"], "%Y-%m-%d %H:%M:%S").date()
            
            # Por ahora retorna False hasta que implementes la API
            return False
            
        except Exception as e:
            logger.error(f"Error verificando fecha: {e}")
            return False

    def get_last_conversation_summary(self, messages: List[Dict]) -> str:
        """
        Crea un resumen de la última conversación para contexto.
        """
        if not messages:
            return "Primera conversación"
        
        # Tomar últimos 3 mensajes para resumen
        recent_messages = messages[-3:]
        
        if len(recent_messages) == 1:
            # Solo un mensaje
            last_msg = recent_messages[0]["content"][:150]
            return f"Último mensaje: {last_msg}"
        
        elif len(recent_messages) >= 2:
            # Múltiples mensajes - crear resumen
            user_messages = [msg["content"] for msg in recent_messages if msg["role"] == "user"]
            bot_messages = [msg["content"] for msg in recent_messages if msg["role"] == "assistant"]
            
            summary_parts = []
            if user_messages:
                last_user_msg = user_messages[-1][:100]
                summary_parts.append(f"Usuario preguntó: {last_user_msg}")
            
            if bot_messages:
                last_bot_msg = bot_messages[-1][:100]
                summary_parts.append(f"Bot respondió: {last_bot_msg}")
            
            return " | ".join(summary_parts)
        
        return "Primera conversación"

    def has_keywords_in_history(self, messages: List[Dict], keywords: List[str]) -> bool:
        """
        Verifica si el historial contiene ciertas palabras clave.
        Útil para detectar temas de conversación recurrentes.
        """
        if not messages or not keywords:
            return False
        
        # Buscar en últimos 10 mensajes
        recent_messages = messages[-10:]
        
        for msg in recent_messages:
            content = msg["content"].lower()
            for keyword in keywords:
                if keyword.lower() in content:
                    return True
        
        return False

    def get_conversation_stats(self, messages: List[Dict]) -> Dict[str, int]:
        """
        Obtiene estadísticas básicas de la conversación.
        """
        if not messages:
            return {
                "total_messages": 0,
                "user_messages": 0,
                "bot_messages": 0,
                "today_messages": 0
            }
        
        user_count = len([msg for msg in messages if msg["role"] == "user"])
        bot_count = len([msg for msg in messages if msg["role"] == "assistant"])
        
        # TODO: Implementar conteo de mensajes de hoy cuando tengas timestamps
        today_count = 0
        
        return {
            "total_messages": len(messages),
            "user_messages": user_count,
            "bot_messages": bot_count,
            "today_messages": today_count
        }