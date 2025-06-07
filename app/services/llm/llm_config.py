from pathlib import Path

class LLMConfig:
    """Configuración mínima para LLM - todo lo demás viene de BD"""
    
    # Solo el directorio donde se descargan los modelos
    MODELS_DIR = Path("models") 