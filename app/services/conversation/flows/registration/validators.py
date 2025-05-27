import logging
from typing import Tuple, Optional
from pydantic import ValidationError
from app.schemas.registration_schema import DocumentSchema, NameSchema, PhoneSchema

logger = logging.getLogger(__name__)

class RegistrationValidators:
    """
    Responsabilidad única: Validaciones específicas del registro.
    Encapsula toda la lógica de validación usando Pydantic schemas.
    """

    @staticmethod
    def validate_document(document: str) -> Tuple[bool, str, Optional[str]]:
        """
        Valida documento de identidad usando DocumentSchema.
        
        Args:
            document: Documento a validar
            
        Returns:
            Tuple[bool, str, Optional[str]]: (is_valid, error_message, cleaned_value)
        """
        try:
            schema = DocumentSchema(VcIdentificationNumber=document)
            cleaned_document = schema.VcIdentificationNumber
            logger.debug(f"Documento validado exitosamente: {cleaned_document}")
            return (True, "", cleaned_document)
        except ValidationError as e:
            error_msg = e.errors()[0]['msg']
            logger.warning(f"Documento inválido '{document}': {error_msg}")
            return (False, error_msg, None)
        except Exception as e:
            logger.error(f"Error inesperado validando documento: {e}")
            return (False, "Error validando documento", None)

    @staticmethod
    def validate_name(name: str) -> Tuple[bool, str, Optional[str]]:
        """
        Valida nombre usando NameSchema.
        
        Args:
            name: Nombre a validar
            
        Returns:
            Tuple[bool, str, Optional[str]]: (is_valid, error_message, cleaned_value)
        """
        try:
            schema = NameSchema(VcFirstName=name)
            cleaned_name = schema.VcFirstName
            logger.debug(f"Nombre validado exitosamente: {cleaned_name}")
            return (True, "", cleaned_name)
        except ValidationError as e:
            error_msg = e.errors()[0]['msg']
            logger.warning(f"Nombre inválido '{name}': {error_msg}")
            return (False, error_msg, None)
        except Exception as e:
            logger.error(f"Error inesperado validando nombre: {e}")
            return (False, "Error validando nombre", None)

    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str, Optional[str]]:
        """
        Valida teléfono usando PhoneSchema.
        
        Args:
            phone: Teléfono a validar
            
        Returns:
            Tuple[bool, str, Optional[str]]: (is_valid, error_message, cleaned_value)
        """
        try:
            schema = PhoneSchema(VcPhone=phone)
            cleaned_phone = schema.VcPhone
            logger.debug(f"Teléfono validado exitosamente: {cleaned_phone}")
            return (True, "", cleaned_phone)
        except ValidationError as e:
            error_msg = e.errors()[0]['msg']
            logger.warning(f"Teléfono inválido '{phone}': {error_msg}")
            return (False, error_msg, None)
        except Exception as e:
            logger.error(f"Error inesperado validando teléfono: {e}")
            return (False, "Error validando teléfono", None)