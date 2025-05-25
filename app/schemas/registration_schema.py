from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError
import re


class DocumentSchema(BaseModel):
    """Schema para validar solo el documento de identidad"""
    VcIdentificationNumber: str

    @field_validator('VcIdentificationNumber')
    def validate_document_id(cls, v):
        v = v.strip()
        if not v:
            raise PydanticCustomError(
                'document_missing',
                'El número de documento es obligatorio'
            )
        if len(v) < 5 or not v.isdigit():
            raise PydanticCustomError(
                'document_invalid',
                'El documento debe contener sólo números y al menos 5 dígitos'
            )
        return v


class NameSchema(BaseModel):
    """Schema para validar solo el nombre"""
    VcFirstName: str

    @field_validator('VcFirstName')
    def validate_first_name(cls, v):
        v = v.strip()
        if not v:
            raise PydanticCustomError(
                'first_name_missing',
                'El nombre es obligatorio'
            )
        if len(v) < 2 or not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', v):
            raise PydanticCustomError(
                'first_name_invalid',
                'El nombre debe contener solo letras'
            )
        return v


class PhoneSchema(BaseModel):
    """Schema para validar solo el teléfono"""
    VcPhone: str

    @field_validator('VcPhone')
    def validate_phone(cls, v):
        v = v.strip()
        if not v:
            raise PydanticCustomError(
                'phone_missing',
                'El número de teléfono es obligatorio'
            )
        # Aceptar con o sin código de país
        if v.startswith('57'):
            if not re.match(r'^57(3|6)\d{9}$', v):
                raise PydanticCustomError(
                    'phone_invalid',
                    "El número debe tener formato 573XXXXXXXXX"
                )
        else:
            if not re.match(r'^(3|6)\d{9}$', v):
                raise PydanticCustomError(
                    'phone_invalid',
                    "El número debe empezar con 3 o 6 y tener 10 dígitos"
                )
            v = f"57{v}"  # Agregar código de país
        return v