# app/logging_config.py
import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

LOG_LEVEL = "DEBUG"           # INFO en producción

# Crear el directorio de logs si no existe
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / "bot.log"

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),                                 # consola
        TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=30, encoding='utf-8'),  # Archivo con rotación diaria y retención de 30 días
    ],
    force=True,    # sobreescribe config que ponga uvicorn
)
