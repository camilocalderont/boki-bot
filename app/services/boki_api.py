import httpx
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

class BokiApiError(Exception):
    """Error al llamar a la API de Boki."""
    pass

class BokiApi:
    """
    Cliente para comunicarse con la API de Boki (bokibot-api).
    Responsabilidad única: comunicación con el backend.
    """

    def __init__(self):

        if settings.API_PORT:
            self.base_url = f"{settings.API_URL}:{settings.API_PORT}/api/v{settings.API_VERSION}"
        else:
            self.base_url = f"{settings.API_URL}/api/v{settings.API_VERSION}"
        self.headers = {
            "Content-Type": "application/json",
            "x-api-token": settings.API_TOKEN
        }

    async def get_client_by_phone(self, phone: str):
        """
        Busca un cliente por número de teléfono.

        Args:
            phone: Número de teléfono del cliente.

        Returns:
            dict: Datos del cliente si está registrado, None si no existe.
        """
        url = f"{self.base_url}/clients/cellphone/{phone}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code == 200:
                    # Estructura de respuesta según bokibot-api
                    return response.json().get("data")
                elif response.status_code == 404 or response.status_code == 409:
                    # Cliente no encontrado (404) o conflicto (409)
                    logger.info(f"Cliente con teléfono {phone} no encontrado. Estado: {response.status_code}")
                    return None
                else:
                    logger.error(f"Error API Boki: {response.status_code} - {response.text}")
                    response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            # Solo registramos el error pero no lo propagamos si es 409
            if exc.response.status_code == 409:
                logger.info(f"Cliente con teléfono {phone} no encontrado (409)")
                return None

            logger.error(f"Error HTTP: {exc.response.status_code} - {exc.response.text}")
            raise BokiApiError(f"Error al comunicarse con la API: {exc.response.text}") from exc
        except httpx.RequestError as exc:
            logger.error(f"Error de conexión: {str(exc)}")
            raise BokiApiError(f"Error de conexión con la API: {str(exc)}") from exc



    async def create_client(self, client_data: dict):
        """
        Crea un nuevo cliente en la API.

        Args:
            client_data: Datos del cliente a crear.

        Returns:
            dict: Datos del cliente creado.
        """
        url = f"{self.base_url}/clients"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, headers=self.headers, json=client_data)
                response.raise_for_status()
                return response.json().get("data")

        except httpx.HTTPStatusError as exc:
            logger.error(f"Error HTTP: {exc.response.status_code} - {exc.response.text}")
            raise BokiApiError(f"Error al crear cliente: {exc.response.text}") from exc
        except httpx.RequestError as exc:
            logger.error(f"Error de conexión: {str(exc)}")
            raise BokiApiError(f"Error de conexión con la API: {str(exc)}") from exc