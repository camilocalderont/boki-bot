from pydantic import BaseModel, Field, validator
import re

class ClientCreate(BaseModel):
    """Modelo para crear un cliente en la API de Boki."""
    VcIdentificationNumber: str = Field(..., min_length=5, max_length=50)
    VcPhone: str = Field(..., min_length=10, max_length=15)
    vcNickName: str = None
    VcFirstName: str = Field(..., min_length=2, max_length=100)
    VcSecondName: str = None
    VcFirstLastName: str = None
    VcSecondLastName: str = None
    VcEmail: str = None

    @validator('VcPhone')
    def validate_phone(cls, v):
        """Valida que el teléfono tenga el formato correcto."""
        if not re.match(r'^57(3|6)\d{9}$', v):
            raise ValueError("El número de teléfono debe tener formato 573XXXXXXXXX (código país + celular)")
        return v