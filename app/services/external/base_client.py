import httpx
import logging
from typing import Dict, Any
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class BokiApiError(Exception):
    """Error al llamar a la API de Boki."""
    pass

class BaseClient:
    """
    Cliente HTTP base para comunicación con la API de Boki.
    Responsabilidad única: configuración HTTP y manejo de errores.
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

        # Cliente HTTP reutilizable con configuración optimizada
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers=self.headers,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

    async def _make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Método centralizado para hacer requests con manejo de errores.
        
        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            url: URL relativa o absoluta
            **kwargs: Argumentos adicionales para httpx
            
        Returns:
            httpx.Response: Respuesta del servidor
            
        Raises:
            BokiApiError: Error de comunicación con la API
        """
        try:
            full_url = url if url.startswith('http') else f"{self.base_url}/{url.lstrip('/')}"
            logger.debug(f"[API] {method} {full_url}")

            response = await self.client.request(method, full_url, **kwargs)
            logger.debug(f"[API] {method} {full_url} -> {response.status_code}")

            if response.status_code >= 400:
                logger.error(f"[API] Error {response.status_code}: {response.text}")

            return response
            
        except httpx.TimeoutException:
            logger.error(f"[API] Timeout en {method} {url}")
            raise BokiApiError(f"Timeout al comunicarse con la API")
        except httpx.RequestError as e:
            logger.error(f"[API] Error de conexión en {method} {url}: {e}")
            raise BokiApiError(f"Error de conexión: {str(e)}")

    async def close(self):
        """Cierra el cliente HTTP."""
        try:
            await self.client.aclose()
            logger.debug("[API] Cliente HTTP cerrado")
        except Exception as e:
            logger.error(f"[API] Error cerrando cliente: {e}")