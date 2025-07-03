import logging
from typing import Tuple, Dict
from .validators import RegistrationValidators

logger = logging.getLogger(__name__)

class RegistrationSteps:
    """
    Responsabilidad única: Lógica de cada paso del registro.
    Coordina validaciones y maneja la progresión entre pasos.
    """

    def __init__(self, boki_api):
        self.boki_api = boki_api

    async def process_document_step(self, message: str, data: Dict) -> Tuple[Dict, str, bool]:
        """
        Procesa el paso de captura de documento de identidad.
        
        Args:
            message: Documento enviado por el usuario
            data: Datos actuales del flujo
            
        Returns:
            Tuple[Dict, str, bool]: (nuevo_estado, respuesta, flujo_completado)
        """
        logger.info(f"Procesando documento: '{message}'")
        
        # Validar documento usando el validador especializado
        is_valid, error_msg, cleaned_document = RegistrationValidators.validate_document(message)
        
        if not is_valid:
            return (
                {"step": "waiting_id", "data": data},
                error_msg,
                False
            )

        # Documento válido, guardar y avanzar al siguiente paso
        data["VcIdentificationNumber"] = cleaned_document
        new_state = {"step": "waiting_name", "data": data}

        logger.info(f"Documento guardado exitosamente: {cleaned_document}")
        
        return (
            new_state,
            "Perfecto. Ahora, por favor proporciona tu primer nombre:",
            False
        )

    async def process_name_step(self, message: str, data: Dict, contact_id: str) -> Tuple[Dict, str, bool]:
        """
        Procesa el paso de captura de nombre y procede a crear el cliente.
        
        Args:
            message: Nombre enviado por el usuario
            data: Datos actuales del flujo
            contact_id: ID del contacto
            
        Returns:
            Tuple[Dict, str, bool]: (nuevo_estado, respuesta, flujo_completado)
        """
        logger.info(f"Procesando nombre: '{message}'")
        
        # Validar nombre usando el validador especializado
        is_valid, error_msg, cleaned_name = RegistrationValidators.validate_name(message)
        
        if not is_valid:
            return (
                {"step": "waiting_name", "data": data},
                error_msg,
                False
            )

        # Nombre válido, guardar y proceder a crear cliente
        data["VcFirstName"] = cleaned_name
        logger.info(f"Nombre guardado exitosamente: {cleaned_name}")
        
        # Proceder inmediatamente a crear el cliente
        return await self._create_client(data, contact_id)

    async def _create_client(self, data: Dict, contact_id: str) -> Tuple[Dict, str, bool]:
        """
        Crea el cliente en el sistema usando la API.
        
        Args:
            data: Datos completos del usuario
            contact_id: ID del contacto
            
        Returns:
            Tuple[Dict, str, bool]: (nuevo_estado, respuesta, flujo_completado)
        """
        try:
            logger.info(f"Iniciando creación de cliente con datos: {data}")

            company_id = data.get("company_id")
            if not company_id:
                logger.error("Error crítico: company_id es obligatorio para crear cliente")
                return await self._restart_registration(
                    data.get("phone", ""), 
                    "Error de configuración. Por favor contacta al soporte técnico."
                )

            # Validar teléfono antes de crear el cliente
            phone = data.get("phone", "")
            is_valid, error_msg, cleaned_phone = RegistrationValidators.validate_phone(phone)
            
            if not is_valid:
                logger.warning(f"Teléfono inválido durante creación: {phone}")
                return await self._restart_registration(phone, error_msg)

            client_data = {
                "VcIdentificationNumber": data["VcIdentificationNumber"],
                "VcPhone": cleaned_phone,
                "VcFirstName": data["VcFirstName"],
                "CompanyId": company_id 
            }

            logger.info(f"Datos del cliente preparados con company_id obligatorio: {client_data}")

            # Crear cliente a través de la API
            result = await self.boki_api.create_client(client_data)
            logger.info(f"Resultado de creación: {result}")

            if result:
                client_id = result.get('Id', 'N/A')
                logger.info(f"Cliente creado exitosamente: {client_id} para company: {company_id}")
                
                # Flujo completado exitosamente
                return (
                    {},  # Estado vacío = flujo completado
                    f"¡Registro completado exitosamente! 🎉\n\n"
                    f"Bienvenido/a {data['VcFirstName']}, tu cuenta ha sido creada correctamente.\n\n"
                    f"Ya puedes agendar citas o hacer preguntas. ¿En qué puedo ayudarte?",
                    True  # Flujo completado
                )
            else:
                logger.error("Error al crear cliente en la API - resultado nulo")
                return await self._restart_registration(
                    data.get("phone", ""), 
                    "No se pudo crear tu cuenta. Intenta nuevamente."
                )

        except Exception as e:
            logger.error(f"Error inesperado creando cliente: {e}", exc_info=True)
            return await self._restart_registration(
                data.get("phone", ""), 
                "Hubo un error técnico. Intenta nuevamente."
            )

    async def _restart_registration(self, phone: str, custom_message: str = None) -> Tuple[Dict, str, bool]:
        """
        Reinicia el flujo de registro desde el principio.
        
        Args:
            phone: Teléfono del usuario
            custom_message: Mensaje personalizado de error
            
        Returns:
            Tuple[Dict, str, bool]: (estado_inicial, mensaje_reinicio, flujo_no_completado)
        """
        logger.info(f"Reiniciando flujo de registro para teléfono: {phone}")
        
        base_message = "Empecemos de nuevo el registro.\n\nPor favor, proporciona tu número de documento de identidad:"
        
        if custom_message:
            full_message = f"❌ {custom_message}\n\n{base_message}"
        else:
            full_message = f"Hubo un error. {base_message}"
        
        restart_data = {"phone": phone}
        # Nota: El company_id se volverá a agregar cuando el FlowRouter procese el mensaje
        
        return (
            {"step": "waiting_id", "data": restart_data},
            full_message,
            False
        )