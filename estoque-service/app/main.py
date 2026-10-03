from fastapi import FastAPI

from app.registro_log import configurar_logs
from app.rotas import router

configurar_logs()

app = FastAPI(title="Estoque Service")
app.include_router(router)
