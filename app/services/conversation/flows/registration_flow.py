# app/services/conversation/flows/registration_flow.py
import logging
from typing import Tuple, Dict, Optional
from app.services.conversation.flows.base_flow import BaseFlow
from app.services.boki_api import BokiApi
from pydantic import ValidationError
from app.schemas.registration_schema import (
    DocumentSchema,
    NameSchema,
    PhoneSchema
)
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

        logger.info(f"[REGISTRO] Procesando documento: '{message}'")
        try:
            # Validar solo el documento
            schema = DocumentSchema(VcIdentificationNumber=message)
            VcIdentificationNumber = schema.VcIdentificationNumber  # Usar el valor validado y limpio

        except ValidationError as e:
            return (
                {"step": "waiting_id", "data": data},
                e.errors()[0]['msg'],  # Mensaje de error del schema
                False
            )

        # Guardar documento y pasar al siguiente paso
        data["VcIdentificationNumber"] = VcIdentificationNumber
        new_state = {"step": "waiting_name", "data": data}

        logger.info(f"[REGISTRO] Documento guardado: {VcIdentificationNumber}")
        logger.info(f"[REGISTRO] Nuevo estado: {new_state}")

        return (
            new_state,
            "Perfecto. Ahora, por favor proporciona tu primer nombre:",
            False
        )

    async def _process_name_step(self, message: str, data: Dict, contact_id: str) -> Tuple[Dict, str, bool]:
        """Procesa el paso de captura de nombre y crea el cliente inmediatamente."""

        logger.info(f"[REGISTRO] Procesando nombre: '{message}'")

        try:
            # Validar solo el nombre
            schema = NameSchema(VcFirstName=message)
            VcFirstName = schema.VcFirstName  # Usar el valor validado y limpio

        except ValidationError as e:
            return (
                {"step": "waiting_name", "data": data},
                e.errors()[0]['msg'],  # Mensaje de error del schema
                False
            )

        data["VcFirstName"] = VcFirstName

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
                phone_schema = PhoneSchema(VcPhone=data.get("phone", ""))
                client_data["VcPhone"] = phone_schema.VcPhone
            except ValidationError as ve:
                logger.warning(f"[REGISTRO] Teléfono inválido: {client_data.VcPhone}")
                return (
                    {"step": "initial", "data": data},
                    e.errors()[0]['msg'],  # Mensaje de error del schema
                    False
                )
            except Exception as ve:
                # Si ClientCreate no está disponible o hay otro error, continuar
                logger.info(f"[REGISTRO] Validación Pydantic no disponible, continuando")

            # Crear cliente
            logger.info(f"[REGISTRO] Enviando solicitud de creación de cliente")
            result = await self.boki_api.create_client(client_data)
            logger.info(f"[REGISTRO] Resultado de creación: {result}")

            if result:
                logger.info(f"[REGISTRO] Cliente creado exitosamente: {result.get('Id')}")
                #Cerrar el flujo
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