from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class LLMResponse:
    """Respuesta simple del LLM"""
    text: str
    model: str
    success: bool = True
    error: Optional[str] = None
    response_time: float = 0.0

async def load_agent_config(llm_api_service, company_id: str, agent_name: str) -> Dict[str, Any]:
    """
    Función simple que trae toda la configuración del agente desde la BD
    
    Args:
        llm_api_service: Servicio para llamar al backend
        company_id: ID de la empresa
        agent_name: Nombre del agente (intent_detection, appointment, etc.)
    
    Returns:
        Diccionario con toda la configuración o None si hay error
    """
    try:
        result = await llm_api_service.get_company_agent_prompt(
            company_id=company_id,
            vc_agent_name=agent_name
        )
        
        if not result or result.get('status') != 'success' or not result.get('data'):
            return None
        
        # Los datos vienen como lista, tomar el primer elemento
        agent_data = result['data'][0] if result['data'] else None
        if not agent_data:
            return None
            
        config = {
            "prompt_template": agent_data.get('TxPromptTemplate', ''),
            "is_active": agent_data.get('BIsActive', True),
            "model_name": agent_data.get('VcModelName'),
            "repo_id": agent_data.get('VcRepoId'),
            "filename": agent_data.get('VcFilename'), 
            "local_name": agent_data.get('VcLocalName'),
            "temperature": float(agent_data.get('DcTemperature', 0.1)),
            "max_tokens": agent_data.get('IMaxTokens', 100),
            "top_p": float(agent_data.get('DcTopP', 0.8)),
            "top_k": agent_data.get('ITopK', 5),
            "context_length": agent_data.get('IContextLength', 1024),
            "stop_tokens": agent_data.get('TxStopTokens', '[]'),
            "max_memory_mb": agent_data.get('IMaxMemoryMb', 6000),
            "n_threads": agent_data.get('INThreads', 2),
            "use_gpu": agent_data.get('BlsUseGpu', False)
        }
        
        return config
        
    except Exception as e:
        return None