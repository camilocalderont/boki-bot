import logging
from typing import Optional, Dict, Any
from app.services.external.base_client import BaseClient, BokiApiError

logger = logging.getLogger(__name__)


class LLMAPIService(BaseClient):

    async def get_company_agent_prompt(self, company_id: str, vc_agent_name: str) -> Optional[Dict[str, Any]]:
        endpoint = f"companyAgent/llm/company/{company_id}"
        
        params = {
            'VcAgentName': vc_agent_name
        }
        
        try:
            logger.info(f"Consultando prompt del agente para compañía {company_id} con agente {vc_agent_name}")
            
            response = await self._make_request("GET", endpoint, params=params)
            
            if response.status_code == 404:
                logger.warning(f"Compañía {company_id} o agente {vc_agent_name} no encontrado")
                return None
            
            if response.status_code >= 400:
                raise BokiApiError(f"Error HTTP {response.status_code}: {response.text}")
            
            result = response.json()
            logger.info(f"Prompt obtenido exitosamente para compañía {company_id}")
            
            return result
               
        except Exception as e:
            logger.error(f"Error inesperado al consultar compañía {company_id}: {e}")
            raise BokiApiError(f"Error inesperado: {str(e)}")




