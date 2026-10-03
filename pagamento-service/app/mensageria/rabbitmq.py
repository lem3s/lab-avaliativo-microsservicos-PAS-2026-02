import logging
import time

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError

from app.config import configuracoes

logger = logging.getLogger(__name__)

EXCHANGE_PEDIDOS = "pedidos.exchange"
EXCHANGE_PEDIDOS_DLX = "pedidos.dlx"
FILA_PEDIDO_CRIADO = "pedido.criado"
FILA_PEDIDO_CRIADO_DLQ = "pedido.criado.dlq"
ROUTING_KEY_PEDIDO_CRIADO = "pedido.criado"

EXCHANGE_PAGAMENTOS = "pagamentos.exchange"
EXCHANGE_PAGAMENTOS_DLX = "pagamentos.dlx"
FILA_PAGAMENTO_PROCESSADO = "pagamento.processado"
FILA_PAGAMENTO_PROCESSADO_DLQ = "pagamento.processado.dlq"
ROUTING_KEY_PAGAMENTO_PROCESSADO = "pagamento.processado"

LIMITE_ENTREGAS = 3


def conectar(tentativas: int = 10, intervalo: float = 3) -> pika.BlockingConnection:
    parametros = pika.URLParameters(configuracoes.rabbitmq_url)
    for tentativa in range(1, tentativas + 1):
        try:
            return pika.BlockingConnection(parametros)
        except AMQPConnectionError:
            logger.warning("RabbitMQ indisponível (tentativa %s/%s)", tentativa, tentativas)
            if tentativa < tentativas:
                time.sleep(intervalo)
    raise AMQPConnectionError("Não foi possível conectar ao RabbitMQ")


def _declarar_fila(
    canal: BlockingChannel,
    exchange: str,
    exchange_dlx: str,
    fila: str,
    fila_dlq: str,
    routing_key: str,
) -> None:
    canal.exchange_declare(exchange=exchange, exchange_type="direct", durable=True)
    canal.exchange_declare(exchange=exchange_dlx, exchange_type="direct", durable=True)

    canal.queue_declare(queue=fila_dlq, durable=True)
    canal.queue_bind(queue=fila_dlq, exchange=exchange_dlx, routing_key=routing_key)

    canal.queue_declare(
        queue=fila,
        durable=True,
        arguments={
            "x-queue-type": "quorum",
            "x-delivery-limit": LIMITE_ENTREGAS,
            "x-dead-letter-exchange": exchange_dlx,
        },
    )
    canal.queue_bind(queue=fila, exchange=exchange, routing_key=routing_key)


def declarar_topologia(canal: BlockingChannel) -> None:
    _declarar_fila(
        canal,
        EXCHANGE_PEDIDOS,
        EXCHANGE_PEDIDOS_DLX,
        FILA_PEDIDO_CRIADO,
        FILA_PEDIDO_CRIADO_DLQ,
        ROUTING_KEY_PEDIDO_CRIADO,
    )
    _declarar_fila(
        canal,
        EXCHANGE_PAGAMENTOS,
        EXCHANGE_PAGAMENTOS_DLX,
        FILA_PAGAMENTO_PROCESSADO,
        FILA_PAGAMENTO_PROCESSADO_DLQ,
        ROUTING_KEY_PAGAMENTO_PROCESSADO,
    )


def propriedades_json(correlation_id: str) -> pika.BasicProperties:
    return pika.BasicProperties(
        content_type="application/json",
        delivery_mode=pika.DeliveryMode.Persistent,
        correlation_id=correlation_id,
    )
