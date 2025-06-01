"""
Descargador automático de modelos GGUF.
Responsabilidad única: Gestionar descarga y verificación de modelos.
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Optional, Tuple
from huggingface_hub import hf_hub_download
import hashlib

logger = logging.getLogger(__name__)

class ModelDownloader:
    """
    Descarga automática de modelos GGUF desde Hugging Face.
    Compatible con la arquitectura existente de LLMManager.
    """

    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Configuración de modelos optimizada para tu VPS 8GB
        self.model_configs = {
            "intent": {
                "repo_id": "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
                "filename": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
                "local_filename": "tinyllama-intent.gguf",
                "expected_size_mb": 700,  # ~700MB
                "description": "Modelo ligero para detección de intenciones"
            },
            "conversation": {
                "repo_id": "TheBloke/Mistral-7B-Instruct-v0.1-GGUF",
                "filename": "mistral-7b-instruct-v0.1.Q4_K_M.gguf",
                "local_filename": "mistral-conversation.gguf",
                "expected_size_mb": 4200,  # ~4.2GB
                "description": "Modelo conversacional principal"
            }
        }

    async def ensure_model_available(self, model_name: str) -> Tuple[bool, str]:
        """
        Asegura que un modelo esté disponible localmente.

        Args:
            model_name: "intent" o "conversation"

        Returns:
            Tuple[bool, str]: (éxito, path_del_modelo)
        """
        try:
            if model_name not in self.model_configs:
                raise ValueError(f"Modelo desconocido: {model_name}")

            config = self.model_configs[model_name]
            local_path = self.models_dir / config["local_filename"]

            # Verificar si ya existe y es válido
            if await self._is_model_valid(local_path, config):
                logger.info(f"✅ Modelo {model_name} ya disponible: {local_path}")
                return True, str(local_path)

            # Descargar modelo
            logger.info(f"📥 Descargando modelo {model_name}...")
            success = await self._download_model(model_name, config, local_path)

            if success:
                logger.info(f"✅ Modelo {model_name} descargado: {local_path}")
                return True, str(local_path)
            else:
                logger.error(f"❌ Error descargando modelo {model_name}")
                return False, ""

        except Exception as e:
            logger.error(f"❌ Error asegurando modelo {model_name}: {e}")
            return False, ""

    async def _download_model(self, model_name: str, config: Dict, local_path: Path) -> bool:
        """Descarga un modelo específico."""
        try:
            logger.info(f"📥 Iniciando descarga: {config['description']}")
            logger.info(f"   Archivo: {config['filename']}")
            logger.info(f"   Tamaño estimado: {config['expected_size_mb']}MB")

            # Ejecutar descarga en thread separado para no bloquear
            loop = asyncio.get_event_loop()

            def download_sync():
                return hf_hub_download(
                    repo_id=config["repo_id"],
                    filename=config["filename"],
                    local_dir=self.models_dir,
                    local_dir_use_symlinks=False
                )

            # Descargar con timeout
            downloaded_path = await asyncio.wait_for(
                loop.run_in_executor(None, download_sync),
                timeout=1800  # 30 minutos máximo
            )

            # Renombrar al nombre local esperado
            Path(downloaded_path).rename(local_path)

            # Verificar descarga
            if await self._is_model_valid(local_path, config):
                logger.info(f"✅ Descarga completada y verificada: {model_name}")
                return True
            else:
                logger.error(f"❌ Modelo descargado pero inválido: {model_name}")
                return False

        except asyncio.TimeoutError:
            logger.error(f"❌ Timeout descargando {model_name} (30 min)")
            return False
        except Exception as e:
            logger.error(f"❌ Error en descarga de {model_name}: {e}")
            return False

    async def _is_model_valid(self, local_path: Path, config: Dict) -> bool:
        """Verifica que un modelo local sea válido."""
        try:
            if not local_path.exists():
                return False

            # Verificar tamaño aproximado
            size_mb = local_path.stat().st_size / (1024 * 1024)
            expected_size = config["expected_size_mb"]

            # Permitir 10% de diferencia en tamaño
            if abs(size_mb - expected_size) > (expected_size * 0.1):
                logger.warning(f"⚠️ Tamaño inesperado: {size_mb}MB vs {expected_size}MB esperados")
                return False

            # Verificar que sea un archivo GGUF válido (header básico)
            with open(local_path, 'rb') as f:
                header = f.read(4)
                if header != b'GGUF':
                    logger.warning(f"⚠️ Archivo no es GGUF válido: {local_path}")
                    return False

            return True

        except Exception as e:
            logger.warning(f"⚠️ Error verificando modelo: {e}")
            return False

    def get_model_info(self) -> Dict[str, Dict]:
        """Obtiene información de todos los modelos configurados."""
        info = {}

        for model_name, config in self.model_configs.items():
            local_path = self.models_dir / config["local_filename"]

            info[model_name] = {
                "description": config["description"],
                "expected_size_mb": config["expected_size_mb"],
                "local_path": str(local_path),
                "exists": local_path.exists(),
                "size_mb": round(local_path.stat().st_size / (1024 * 1024), 1) if local_path.exists() else 0
            }

        return info

    async def download_all_models(self) -> Dict[str, bool]:
        """Descarga todos los modelos configurados."""
        results = {}

        for model_name in self.model_configs.keys():
            success, _ = await self.ensure_model_available(model_name)
            results[model_name] = success

        return results