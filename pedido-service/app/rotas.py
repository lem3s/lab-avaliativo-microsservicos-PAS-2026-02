import logging
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pika.exceptions import AMQPError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.banco import obter_sessao
from app.clientes import estoque
from app.clientes.estoque import ErroEstoque
from app.config import configuracoes
from app.esquemas import Mensagem, PedidoCriadoEvento, PedidoEntrada, PedidoSaida
from app.mensageria.publicador import publicador
from app.modelos import Pedido, StatusPedido

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


class FalhaSimulada(Exception):
    pass


@router.post(
    "",
    status_code=201,
    response_model=PedidoSaida,
    responses={
        404: {"model": Mensagem},
        409: {"model": Mensagem},
        500: {"model": Mensagem},
        503: {"model": Mensagem},
    },
)
def criar_pedido(entrada: PedidoEntrada, sessao: Session = Depends(obter_sessao)):
    correlation_id = str(uuid.uuid4())
    logger.info(
        "correlationId=%s Requisição de pedido recebida: produto %s, quantidade %s",
        correlation_id,
        entrada.produto_id,
        entrada.quantidade,
    )

    try:
        estoque.reservar(entrada.produto_id, entrada.quantidade, correlation_id)
    except ErroEstoque as erro:
        logger.warning(
            "correlationId=%s Pedido não criado: %s", correlation_id, erro.mensagem
        )
        return JSONResponse(status_code=erro.status_code, content={"mensagem": erro.mensagem})

    try:
        if configuracoes.simular_falha_apos_reserva:
            raise FalhaSimulada("Falha simulada após a reserva do estoque")

        pedido = Pedido(
            produto_id=entrada.produto_id,
            quantidade=entrada.quantidade,
            status=StatusPedido.AGUARDANDO_PAGAMENTO,
            correlation_id=correlation_id,
        )
        sessao.add(pedido)
        sessao.commit()
    except Exception:
        sessao.rollback()
        logger.exception("correlationId=%s Falha ao criar o pedido após a reserva", correlation_id)
        if configuracoes.compensacao_habilitada:
            estoque.liberar(entrada.produto_id, entrada.quantidade, correlation_id)
        else:
            logger.warning("correlationId=%s Compensação desabilitada, estoque não liberado", correlation_id)
        return JSONResponse(status_code=500, content={"mensagem": "Erro ao criar pedido"})

    logger.info("correlationId=%s Pedido %s criado", correlation_id, pedido.id)

    evento = PedidoCriadoEvento(
        pedido_id=pedido.id,
        produto_id=pedido.produto_id,
        quantidade=pedido.quantidade,
        correlation_id=correlation_id,
    )
    try:
        publicador.publicar_pedido_criado(evento)
        logger.info("correlationId=%s Evento publicado %s", correlation_id, pedido.id)
    except AMQPError:
        logger.exception(
            "correlationId=%s Falha ao publicar evento pedido.criado do pedido %s",
            correlation_id,
            pedido.id,
        )

    return pedido


@router.get("", response_model=list[PedidoSaida])
def listar_pedidos(sessao: Session = Depends(obter_sessao)):
    return sessao.scalars(select(Pedido).order_by(Pedido.id)).all()


@router.get("/{pedido_id}", response_model=PedidoSaida, responses={404: {"model": Mensagem}})
def buscar_pedido(pedido_id: int, sessao: Session = Depends(obter_sessao)):
    pedido = sessao.get(Pedido, pedido_id)
    if pedido is None:
        return JSONResponse(status_code=404, content={"mensagem": "Pedido inexistente"})
    return pedido
