from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.mensageria.consumidor import iniciar_consumidor
from app.mensageria.publicador import publicador
from app.registro_log import configurar_logs
from app.rotas import router

configurar_logs()


@asynccontextmanager
async def lifespan(app: FastAPI):
    iniciar_consumidor()
    yield
    publicador.fechar()


app = FastAPI(title="Pedido Service", lifespan=lifespan)
app.include_router(router)
