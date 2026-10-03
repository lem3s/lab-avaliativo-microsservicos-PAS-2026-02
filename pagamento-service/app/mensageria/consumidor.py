import logging
import time

from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPError

from app.esquemas import PagamentoProcessadoEvento, PedidoCriadoEvento
from app.mensageria.rabbitmq import (
    EXCHANGE_PAGAMENTOS,
    FILA_PEDIDO_CRIADO,
    ROUTING_KEY_PAGAMENTO_PROCESSADO,
    conectar,
    declarar_topologia,
    propriedades_json,
)
from app.modelos import Pagamento
from app.processamento import processar_pagamento

logger = logging.getLogger(__name__)


def publicar_resultado(canal: BlockingChannel, pagamento: Pagamento) -> None:
    evento = PagamentoProcessadoEvento(
        pedido_id=pagamento.pedido_id,
        status=pagamento.status,
        correlation_id=pagamento.correlation_id,
    )
    canal.basic_publish(
        exchange=EXCHANGE_PAGAMENTOS,
        routing_key=ROUTING_KEY_PAGAMENTO_PROCESSADO,
        body=evento.model_dump_json(by_alias=True),
        properties=propriedades_json(evento.correlation_id),
        mandatory=True,
    )
    logger.info(
        "correlationId=%s Evento pagamento.processado publicado %s",
        evento.correlation_id,
        evento.pedido_id,
    )


def ao_receber_mensagem(canal: BlockingChannel, metodo, propriedades, corpo: bytes) -> None:
    tentativa = (propriedades.headers or {}).get("x-delivery-count", 0) + 1
    try:
        evento = PedidoCriadoEvento.model_validate_json(corpo)
        logger.info(
            "correlationId=%s Evento pedido.criado recebido para o pedido %s (tentativa %s)",
            evento.correlation_id,
            evento.pedido_id,
            tentativa,
        )
        pagamento = processar_pagamento(evento)
        publicar_resultado(canal, pagamento)
        canal.basic_ack(delivery_tag=metodo.delivery_tag)
    except Exception:
        logger.exception(
            "correlationId=%s Falha ao processar pagamento (tentativa %s)",
            propriedades.correlation_id,
            tentativa,
        )
        canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=True)


def consumir() -> None:
    while True:
        try:
            conexao = conectar()
            canal = conexao.channel()
            declarar_topologia(canal)
            canal.confirm_delivery()
            canal.basic_qos(prefetch_count=1)
            canal.basic_consume(queue=FILA_PEDIDO_CRIADO, on_message_callback=ao_receber_mensagem)
            logger.info("Consumindo fila %s", FILA_PEDIDO_CRIADO)
            canal.start_consuming()
        except AMQPError as erro:
            logger.warning("Conexão com o RabbitMQ perdida (%s), reconectando em 5s", erro)
            time.sleep(5)
