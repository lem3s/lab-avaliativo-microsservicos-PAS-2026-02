import logging
import threading
import time

from pika.exceptions import AMQPError

from app.banco import SessaoLocal
from app.clientes import estoque
from app.esquemas import PagamentoProcessadoEvento
from app.mensageria.rabbitmq import FILA_PAGAMENTO_PROCESSADO, conectar, declarar_topologia
from app.modelos import Pedido, StatusPedido

logger = logging.getLogger(__name__)

STATUS_POR_RESULTADO = {
    "APROVADO": StatusPedido.PAGO,
    "REJEITADO": StatusPedido.REJEITADO,
}


def atualizar_pedido(evento: PagamentoProcessadoEvento) -> None:
    with SessaoLocal() as sessao:
        pedido = sessao.get(Pedido, evento.pedido_id)
        if pedido is None:
            logger.warning(
                "correlationId=%s Pedido %s não encontrado, evento ignorado",
                evento.correlation_id,
                evento.pedido_id,
            )
            return
        if pedido.status != StatusPedido.AGUARDANDO_PAGAMENTO:
            logger.info(
                "correlationId=%s Pedido %s já está %s, evento ignorado",
                evento.correlation_id,
                pedido.id,
                pedido.status,
            )
            return

        pedido.status = STATUS_POR_RESULTADO[evento.status]
        sessao.commit()

    logger.info(
        "correlationId=%s Pedido %s atualizado para %s",
        evento.correlation_id,
        pedido.id,
        pedido.status,
    )

    if pedido.status == StatusPedido.REJEITADO:
        estoque.liberar(pedido.produto_id, pedido.quantidade, evento.correlation_id)


def ao_receber_mensagem(canal, metodo, propriedades, corpo: bytes) -> None:
    try:
        evento = PagamentoProcessadoEvento.model_validate_json(corpo)
        logger.info(
            "correlationId=%s Evento pagamento.processado recebido para o pedido %s: %s",
            evento.correlation_id,
            evento.pedido_id,
            evento.status,
        )
        atualizar_pedido(evento)
        canal.basic_ack(delivery_tag=metodo.delivery_tag)
    except Exception:
        logger.exception(
            "correlationId=%s Falha ao processar evento pagamento.processado",
            propriedades.correlation_id,
        )
        canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=True)


def _consumir() -> None:
    while True:
        try:
            conexao = conectar()
            canal = conexao.channel()
            declarar_topologia(canal)
            canal.basic_qos(prefetch_count=1)
            canal.basic_consume(queue=FILA_PAGAMENTO_PROCESSADO, on_message_callback=ao_receber_mensagem)
            logger.info("Consumindo fila %s", FILA_PAGAMENTO_PROCESSADO)
            canal.start_consuming()
        except AMQPError as erro:
            logger.warning("Conexão com o RabbitMQ perdida (%s), reconectando em 5s", erro)
            time.sleep(5)


def iniciar_consumidor() -> None:
    threading.Thread(target=_consumir, name="consumidor-pagamentos", daemon=True).start()
