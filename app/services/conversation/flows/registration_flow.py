import logging
from app.services.conversation.flows.base_flow import BaseFlow
from app.services.boki_api import BokiApi, BokiApiError
from app.models.client import ClientCreate
from pydantic import ValidationError
from typing import Tuple
import re

logger = logging.getLogger(__name__)

class RegistrationFlow(BaseFlow):
    """Implementa el flujo de registro de usuario."""

    def __init__(self):
        self.boki_api = BokiApi()

    async def process_message(self, state: dict, message: str, contact_id: str) -> Tuple[dict, str, bool]:
        """Procesa un mensaje en el flujo de registro."""
        
        current_step = state.get("step")
        data = state.get("data", {})
        
        
        if current_step == "waiting_id":
            # Validar ID mínimo 5 caracteres
            if len(message.strip()) < 5:
                return state, "El número de documento debe tener al menos 5 caracteres. Por favor, proporciona un documento válido:", False
            
            # Guardar ID del documento
            data["VcIdentificationNumber"] = message.strip()
            
            new_state = {
                "step": "waiting_name",
                "data": data
            }
            return new_state, "Gracias. Ahora, por favor proporciona tu **nombre completo**:", False
            
        elif current_step == "waiting_name":
            # Validar nombre mínimo 2 caracteres
            if len(message.strip()) < 2:
                return state, "El nombre completo debe tener al menos 2 caracteres. Por favor, proporciona tu nombre completo:", False
            
            # Dividir nombre completo en primer y segundo nombre
            nombres = message.strip().split()
            if len(nombres) >= 1:
                data["VcFirstName"] = nombres[0]
                data["VcSecondName"] = nombres[1] if len(nombres) >= 2 else None
                # Usar el primer nombre como nickname
                data["vcNickName"] = nombres[0]
                
            
            new_state = {
                "step": "waiting_lastname", 
                "data": data
            }
            return new_state, "Perfecto. Ahora proporciona tus **apellidos completos**:", False
            
        elif current_step == "waiting_lastname":
            # Validar apellidos mínimo 2 caracteres
            if len(message.strip()) < 2:
                return state, "Los apellidos deben tener al menos 2 caracteres. Por favor, proporciona tus apellidos completos:", False
            
            # Dividir apellidos en primer y segundo apellido
            apellidos = message.strip().split()
            if len(apellidos) >= 1:
                data["VcFirstLastName"] = apellidos[0]
                data["VcSecondLastName"] = apellidos[1] if len(apellidos) >= 2 else None
                
            
            new_state = {
                "step": "waiting_email",
                "data": data
            }
            return new_state, "Excelente. Por último, proporciona tu **email**:", False
            
        elif current_step == "waiting_email":
            # Validar formato de email básico
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, message.strip()):
                return state, "Por favor, proporciona un email válido (ejemplo: usuario@gmail.com):", False
            
            # Guardar email
            data["VcEmail"] = message.strip()
            phone = data["VcPhone"]
            
            # Preparar datos completos para crear cliente
            client_data = {
                "VcIdentificationNumber": data["VcIdentificationNumber"],
                "VcPhone": data["VcPhone"],
                "vcNickName": data["vcNickName"],
                "VcFirstName": data["VcFirstName"], 
                "VcSecondName": data["VcSecondName"],
                "VcFirstLastName": data["VcFirstLastName"],
                "VcSecondLastName": data["VcSecondLastName"],
                "VcEmail": data["VcEmail"]
            }
            
            try:
                # Validar datos con Pydantic antes de enviar
                client_model = ClientCreate(**client_data)
                
                # Crear cliente en PostgreSQL
                result = await self.boki_api.create_client(client_data)
                
                if result:
                    return {}, f"¡Registro completado exitosamente! 🎉 Bienvenido/a {data['VcFirstName']} {data['VcFirstLastName']}, tu cuenta ha sido creada correctamente.", True
                else:
                    logger.error(f"[REGISTRO] Error creando cliente")
                    # Reiniciar flujo en caso de error
                    new_state = {"step": "waiting_id", "data": {"phone": phone}}
                    return new_state, "Hubo un error al procesar tu registro. Por favor, intenta nuevamente. Proporciona tu número de documento:", False
                    
            except ValidationError as e:
                logger.error(f"[REGISTRO] Error de validación: {str(e)}")
                # Reiniciar flujo en caso de error de validación
                new_state = {"step": "waiting_id", "data": {"phone": phone}}
                return new_state, "Los datos proporcionados no son válidos. Por favor, comencemos de nuevo. Proporciona tu número de documento:", False
            except Exception as e:
                logger.error(f"[REGISTRO] Error creando cliente: {str(e)}")
                # Reiniciar flujo en caso de error general
                new_state = {"step": "waiting_id", "data": {"phone": phone}}
                return new_state, "Hubo un error al procesar tu registro. Por favor, intenta nuevamente. Proporciona tu número de documento:", False
        
        # Paso desconocido, reiniciar
        logger.warning(f"[REGISTRO] Paso desconocido: {current_step}")
        new_state = {"step": "waiting_id", "data": {"phone": data.get("phone", "")}}
        return new_state, "Empecemos el proceso de registro. Proporciona tu número de documento:", False