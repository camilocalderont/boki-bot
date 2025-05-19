from pydantic import BaseModel, Field, validator
import re

class ClientCreate(BaseModel):
    """Modelo para crear un cliente en la API de Boki."""
    VcIdentificationNumber: str = Field(..., min_length=5, max_length=50)
    VcPhone: str = Field(..., min_length=10, max_length=15)
    VcFirstName: str = Field(..., min_length=2, max_length=100)
    VcNickName: str = None
    VcSecondName: str = None
    VcFirstLastName: str = None
    VcSecondLastName: str = None
    VcEmail: str = None

    @validator('VcPhone')
    def validate_phone(cls, v):
        """Valida que el teléfono tenga el formato correcto."""
        # Comienza con 3 o 6 y tiene 10 dígitos en total
        if not re.match(r'^(3|6)\d{9}$', v):
            raise ValueError("El número de teléfono debe tener 10 dígitos y comenzar con 3 (celular) o 6 (fijo)")
        return v