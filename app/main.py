import app.logging_config
from fastapi import FastAPI
from app.api.v1.webhook import router as webhook_router

app = FastAPI(title="BokiBot – WhatsApp")

app.include_router(webhook_router)

@app.get("/")
async def root():
    return {"message": "BokiBot – WhatsApp"}


