import logging
import random

from sqlalchemy import select

from app.banco import SessaoLocal
from app.config import configuracoes
from app.esquemas import PedidoCriadoEvento
from app.modelos import Pagamento, StatusPagamento

logger = logging.getLogger(__name__)


class FalhaSimulada(Exception):
    pass


def decidir_status() -> StatusPagamento:
    if random.random() < configuracoes.taxa_aprovacao:
        return StatusPagamento.APROVADO
    return StatusPagamento.REJEITADO


def processar_pagamento(evento: PedidoCriadoEvento) -> Pagamento:
    if evento.pedido_id == configuracoes.pagamento_falhar_pedido_id:
        raise FalhaSimulada(f"Falha simulada no processamento do pedido {evento.pedido_id}")

    with SessaoLocal() as sessao:
        existente = sessao.scalar(select(Pagamento).where(Pagamento.pedido_id == evento.pedido_id))
        if existente is not None:
            logger.info(
                "correlationId=%s Pagamento do pedido %s já registrado (%s), reenviando resultado",
                evento.correlation_id,
                evento.pedido_id,
                existente.status,
            )
            return existente

        pagamento = Pagamento(
            pedido_id=evento.pedido_id,
            status=decidir_status(),
            correlation_id=evento.correlation_id,
        )
        sessao.add(pagamento)
        sessao.commit()

    if pagamento.status == StatusPagamento.APROVADO:
        logger.info("correlationId=%s Pagamento aprovado %s", evento.correlation_id, evento.pedido_id)
    else:
        logger.info("correlationId=%s Pagamento rejeitado %s", evento.correlation_id, evento.pedido_id)
    return pagamento
