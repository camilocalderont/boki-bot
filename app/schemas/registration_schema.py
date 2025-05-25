from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError
import re


class DocumentSchema(BaseModel):
    """Schema para validar solo el documento de identidad"""
    VcIdentificationNumber: str = Field(..., min_length=5)

    @field_validator('VcIdentificationNumber')
    def validate_document_id(cls, v):
        v = v.strip()
        if len(v) < 5 or not v.isdigit():
            raise PydanticCustomError(
                'document_invalid',
                'El documento debe contener solo números y debe tener más de 5 dígitos'
            )
        return v


class NameSchema(BaseModel):
    """Schema para validar solo el nombre"""
    VcFirstName: str = Field(..., min_length=2)

    @field_validator('VcFirstName')
    def validate_first_name(cls, v):
        v = v.strip()
        if len(v) < 2 or not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', v):
            raise PydanticCustomError(
                'first_name_invalid',
                'El nombre debe contener solo letras y debe ser mayor a 2 caracteres'
            )
        return v


class PhoneSchema(BaseModel):
    """Schema para validar solo el teléfono"""
    VcPhone: str = Field(..., min_length=10, max_length=15)

    @field_validator('VcPhone')
    def validate_phone(cls, v):
        v = v.strip()
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