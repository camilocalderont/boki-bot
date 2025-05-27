import app.logging_config
import os
import pytz
import logging
from datetime import datetime
from fastapi import FastAPI
from app.api.v1.webhook import router as webhook_router

os.environ['TZ'] = 'America/Bogota'
COLOMBIA_TZ = pytz.timezone('America/Bogota')

logger = logging.getLogger(__name__)
colombia_time = datetime.now(COLOMBIA_TZ)
logger.info(f"[TIMEZONE] Configurado timezone de Colombia. Hora actual: {colombia_time.strftime('%d/%m/%Y %H:%M:%S %Z')}")

app = FastAPI(title="BokiBot – WhatsApp")

app.include_router(webhook_router)

@app.get("/")
async def root():
    return {"message": "BokiBot – WhatsApp"}