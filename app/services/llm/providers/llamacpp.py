# app/services/llm/providers/llamacpp.py - VERSIÓN EXTREMA
import time
import json
from .base import LLMResponse
from ..models.downloader import ModelDownloader

class LlamaCppProvider:
    """Proveedor dinámico para LLM"""
    
    def __init__(self):
        self.downloader = ModelDownloader()
        self.model = None
        self.config = None
    
    async def initialize(self, config: dict):
        """
        Inicializa el proveedor con configuración dinámica
        
        Args:
            config: Configuración desde la BD
        """
        self.config = config
    
    async def generate(self, prompt: str) -> LLMResponse:
        """Genera respuesta usando configuración dinámica"""
        if not self.config:
            return LLMResponse(text="", model="unknown", success=False, error="Proveedor no inicializado")
        
        start_time = time.time()
        
        try:
            # Cargar modelo si no está cargado
            if not self.model:
                await self._load_model()
            
            # Procesar stop tokens
            stop_tokens = self._get_stop_tokens()
            
            # Generar respuesta con configuración dinámica
            response = self.model(
                prompt, 
                max_tokens=self.config.get('max_tokens', 100),
                temperature=self.config.get('temperature', 0.1),
                top_p=self.config.get('top_p', 0.8),
                top_k=self.config.get('top_k', 5),
                stop=stop_tokens
            )
            
            text = response["choices"][0]["text"].strip()
            
            return LLMResponse(
                text=text,
                model=self.config.get('model_name', 'unknown'), 
                response_time=time.time() - start_time,
                success=True
            )
            
        except Exception as e:
            return LLMResponse(
                text="", 
                model=self.config.get('model_name', 'unknown'), 
                success=False, 
                error=str(e)
            )
    
    async def _load_model(self):
        """Carga el modelo usando configuración dinámica"""
        model_info = {
            'repo_id': self.config.get('repo_id'),
            'filename': self.config.get('filename'),
            'local_name': self.config.get('local_name')
        }
        
        success, model_path = await self.downloader.ensure_model_available_dynamic(model_info)
        if not success:
            raise Exception(f"No se pudo descargar modelo: {self.config.get('model_name')}")
        
        from llama_cpp import Llama
        self.model = Llama(
            model_path=model_path,
            n_ctx=self.config.get('context_length', 1024),
            n_threads=self.config.get('n_threads', 2),
            use_mlock=not self.config.get('use_gpu', False),  # Si no usa GPU, usar mlock
            verbose=False
        )
    
    def _get_stop_tokens(self) -> list:
        """Procesa stop tokens desde configuración"""
        stop_tokens_str = self.config.get('stop_tokens', '[]')
        
        try:
            if isinstance(stop_tokens_str, str):
                return json.loads(stop_tokens_str)
            elif isinstance(stop_tokens_str, list):
                return stop_tokens_str
            else:
                return []
        except json.JSONDecodeError:
            return []