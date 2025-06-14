import logging
from app.services.external.base_client import BaseClient, BokiApiError


logger = logging.getLogger(__name__)

class CompanyApiService(BaseClient):

    async def get_company_id(self, number_id: str) -> str:
        endpoint = f"companyWhatsappSetting/llm/phone-number/{number_id}"
        try:
            response = await self._make_request("GET", endpoint)
            return response.json()["data"]["CompanyId"]
        except BokiApiError as e:
            logger.error(f"Error getting company id: {e}")
            raise e
