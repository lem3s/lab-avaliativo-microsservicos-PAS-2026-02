import logging
import threading

import pika
from pika.exceptions import AMQPError

from app.esquemas import PedidoCriadoEvento
from app.mensageria.rabbitmq import (
    EXCHANGE_PEDIDOS,
    ROUTING_KEY_PEDIDO_CRIADO,
    conectar,
    declarar_topologia,
    propriedades_json,
)

logger = logging.getLogger(__name__)


class PublicadorPedidos:
    def __init__(self):
        self._trava = threading.Lock()
        self._conexao: pika.BlockingConnection | None = None
        self._canal = None

    def publicar_pedido_criado(self, evento: PedidoCriadoEvento) -> None:
        with self._trava:
            try:
                self._enviar(evento)
            except AMQPError:
                logger.warning(
                    "correlationId=%s Conexão com o RabbitMQ perdida, tentando novamente",
                    evento.correlation_id,
                )
                self._fechar()
                self._enviar(evento)

    def fechar(self) -> None:
        with self._trava:
            self._fechar()

    def _enviar(self, evento: PedidoCriadoEvento) -> None:
        self._abrir_canal()
        self._canal.basic_publish(
            exchange=EXCHANGE_PEDIDOS,
            routing_key=ROUTING_KEY_PEDIDO_CRIADO,
            body=evento.model_dump_json(by_alias=True),
            properties=propriedades_json(evento.correlation_id),
            mandatory=True,
        )

    def _abrir_canal(self) -> None:
        if self._conexao is not None and self._conexao.is_open and self._canal.is_open:
            return
        self._fechar()
        self._conexao = conectar(tentativas=3, intervalo=1)
        self._canal = self._conexao.channel()
        self._canal.confirm_delivery()
        declarar_topologia(self._canal)

    def _fechar(self) -> None:
        if self._conexao is not None and self._conexao.is_open:
            try:
                self._conexao.close()
            except AMQPError:
                pass
        self._conexao = None
        self._canal = None


publicador = PublicadorPedidos()
