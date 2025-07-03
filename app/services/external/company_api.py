import logging
from .base_client import BaseClient, BokiApiError

logger = logging.getLogger(__name__)

class CompanyApiService(BaseClient):
    """
    Cliente para gestión de configuraciones de WhatsApp de empresa.
    Responsabilidad única: operaciones relacionadas con company settings.
    """

    async def get_company_id(self, number_id: str) -> str:
        """
        Obtiene el company_id basado en el number_id de WhatsApp.
        
        Args:
            number_id: ID del número de WhatsApp de Meta
            
        Returns:
            str: ID de la empresa
            
        Raises:
            BokiApiError: Si no se puede obtener el company_id
        """
        endpoint = f"companyWhatsappSetting/llm/phone-number/{number_id}"
        try:
            response = await self._make_request("GET", endpoint)
            company_id = response.json()["data"]["CompanyId"]
            logger.debug(f"[COMPANY] Company ID obtenido: {company_id} para number_id: {number_id}")
            return str(company_id)
        except BokiApiError as e:
            logger.error(f"[COMPANY] Error obteniendo company_id para number_id {number_id}: {e}")
            raise e