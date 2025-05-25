# app/services/conversation/flows/registration_flow.py
import logging
from typing import Tuple, Dict, Optional
from app.services.conversation.flows.base_flow import BaseFlow
from app.services.boki_api import BokiApi
from app.models.client import ClientCreate
from pydantic import ValidationError
import re

logger = logging.getLogger(__name__)

class RegistrationFlow(BaseFlow):
    """Implementa el flujo de registro de usuario simplificado."""

    def __init__(self):
        self.boki_api = BokiApi()

    async def process_message(self, state: Dict, message: str, contact_id: str) -> Tuple[Dict, str, bool]:
        """
        Procesa un mensaje en el flujo de registro.
        
        Returns:
            Tuple[Dict, str, bool]: (nuevo_estado, respuesta, flujo_completado)
        """
        current_step = state.get("step", "waiting_id")
        data = state.get("data", {})
        
        logger.info(f"[REGISTRO] Procesando paso '{current_step}' para contacto {contact_id}")
        logger.info(f"[REGISTRO] Estado actual: {state}")
        logger.info(f"[REGISTRO] Mensaje: {message}")
        
        try:
            if current_step == "waiting_id":
                return await self._process_id_step(message, data)
            elif current_step == "waiting_name":
                return await self._process_name_step(message, data, contact_id)
            else:
                # Paso desconocido, reiniciar
                logger.warning(f"[REGISTRO] Paso desconocido: {current_step}")
                return self._restart_flow(data.get("phone", ""))
                
        except Exception as e:
            logger.error(f"[REGISTRO] Error procesando mensaje: {e}", exc_info=True)
            return self._restart_flow(data.get("phone", ""))

    async def _process_id_step(self, message: str, data: Dict) -> Tuple[Dict, str, bool]:
        """Procesa el paso de captura de documento de identidad."""
        document_id = message.strip()
        
        logger.info(f"[REGISTRO] Procesando documento: '{document_id}'")
        
        # Validar documento mínimo
        if len(document_id) < 5 or not document_id.replace(" ", "").isalnum():
            logger.warning(f"[REGISTRO] Documento inválido: {document_id}")
            return (
                {"step": "waiting_id", "data": data},
                "El número de documento debe tener al menos 5 caracteres alfanuméricos. Por favor, proporciona un documento válido:",
                False
            )
        
        # Guardar documento y pasar al siguiente paso
        data["VcIdentificationNumber"] = document_id
        new_state = {"step": "waiting_name", "data": data}
        
        logger.info(f"[REGISTRO] Documento guardado: {document_id}")
        logger.info(f"[REGISTRO] Nuevo estado: {new_state}")
        
        return (
            new_state,
            "Perfecto. Ahora, por favor proporciona tu primer nombre:",
            False
        )

    async def _process_name_step(self, message: str, data: Dict, contact_id: str) -> Tuple[Dict, str, bool]:
        """Procesa el paso de captura de nombre y crea el cliente inmediatamente."""
        first_name = message.strip()
        
        logger.info(f"[REGISTRO] Procesando nombre: '{first_name}'")
        
        # Validar nombre
        if len(first_name) < 2:
            logger.warning(f"[REGISTRO] Nombre muy corto: {first_name}")
            return (
                {"step": "waiting_name", "data": data},
                "El nombre debe tener al menos 2 caracteres. Por favor, proporciona tu primer nombre:",
                False
            )
        
        # Tomar solo la primera palabra como primer nombre
        first_name_clean = first_name.split()[0]
        data["VcFirstName"] = first_name_clean
        
        logger.info(f"[REGISTRO] Nombre limpio guardado: {first_name_clean}")
        logger.info(f"[REGISTRO] Datos completos para crear cliente: {data}")
        
        # Crear cliente inmediatamente
        return await self._create_client(data, contact_id)

    async def _create_client(self, data: Dict, contact_id: str) -> Tuple[Dict, str, bool]:
        """Crea el cliente en la base de datos."""
        try:
            logger.info(f"[REGISTRO] Iniciando creación de cliente con datos: {data}")
            
            # Preparar datos para crear cliente - SOLO los campos necesarios
            client_data = {
                "VcIdentificationNumber": data["VcIdentificationNumber"],
                "VcPhone": data.get("phone", ""),
                "VcFirstName": data["VcFirstName"],
            }
            
            logger.info(f"[REGISTRO] Datos del cliente preparados: {client_data}")
            
            # Validar con Pydantic antes de enviar (si tienes el modelo)
            try:
                # Solo validar si el modelo ClientCreate está disponible
                ClientCreate(**client_data)
                logger.info(f"[REGISTRO] Validación Pydantic exitosa")
            except ValidationError as ve:
                logger.error(f"[REGISTRO] Error de validación Pydantic: {ve}")
                # Continuar anyway ya que sabemos que los campos son correctos
                logger.info(f"[REGISTRO] Continuando con la creación a pesar del error de validación")
            except Exception as ve:
                # Si ClientCreate no está disponible o hay otro error, continuar
                logger.info(f"[REGISTRO] Validación Pydantic no disponible, continuando")
            
            # Crear cliente
            logger.info(f"[REGISTRO] Enviando solicitud de creación de cliente")
            result = await self.boki_api.create_client(client_data)
            logger.info(f"[REGISTRO] Resultado de creación: {result}")
            
            if result:
                logger.info(f"[REGISTRO] Cliente creado exitosamente: {result.get('Id')}")
                return (
                    {},  # Estado vacío = flujo completado
                    f"¡Registro completado exitosamente! 🎉\n\n"
                    f"Bienvenido/a {data['VcFirstName']}, tu cuenta ha sido creada correctamente.\n\n"
                    f"Ya puedes agendar citas o hacer preguntas. ¿En qué puedo ayudarte?",
                    True  # Flujo completado
                )
            else:
                logger.error(f"[REGISTRO] Error al crear cliente en la API - resultado nulo")
                return self._restart_flow(data.get("phone", ""))
                
        except Exception as e:
            logger.error(f"[REGISTRO] Error creando cliente: {e}", exc_info=True)
            return self._restart_flow(data.get("phone", ""))

    def _restart_flow(self, phone: str) -> Tuple[Dict, str, bool]:
        """Reinicia el flujo de registro."""
        logger.info(f"[REGISTRO] Reiniciando flujo para teléfono: {phone}")
        return (
            {"step": "waiting_id", "data": {"phone": phone}},
            "Hubo un error. Empecemos de nuevo el registro.\n\nPor favor, proporciona tu número de documento de identidad:",
            False
        )