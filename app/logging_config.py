# app/logging_config.py
import logging
from pathlib import Path

LOG_LEVEL = "DEBUG"           # INFO en producción

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),                                 # consola
        logging.FileHandler(Path(__file__).parent / "bot.log"),  # archivo opcional
    ],
    force=True,    # sobreescribe config que ponga uvicorn
)
