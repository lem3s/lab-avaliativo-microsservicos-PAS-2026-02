import logging

import requests

from app.config import configuracoes

logger = logging.getLogger(__name__)

TIMEOUT_SEGUNDOS = 5


class ErroEstoque(Exception):
    def __init__(self, status_code: int, mensagem: str):
        super().__init__(mensagem)
        self.status_code = status_code
        self.mensagem = mensagem


def _url_produto(produto_id: int, acao: str) -> str:
    return f"{configuracoes.estoque_service_url}/produtos/{produto_id}/{acao}"


def reservar(produto_id: int, quantidade: int, correlation_id: str) -> None:
    try:
        resposta = requests.put(
            _url_produto(produto_id, "reservar"),
            json={"quantidade": quantidade},
            headers={"X-Correlation-Id": correlation_id},
            timeout=TIMEOUT_SEGUNDOS,
        )
    except requests.RequestException as erro:
        logger.error("correlationId=%s Estoque Service indisponível: %s", correlation_id, erro)
        raise ErroEstoque(503, "Estoque Service indisponível") from erro

    if resposta.status_code in (404, 409):
        raise ErroEstoque(resposta.status_code, resposta.json()["mensagem"])
    if not resposta.ok:
        logger.error(
            "correlationId=%s Resposta inesperada do Estoque Service: %s",
            correlation_id,
            resposta.status_code,
        )
        raise ErroEstoque(502, "Erro ao reservar estoque")


def liberar(produto_id: int, quantidade: int, correlation_id: str) -> None:
    try:
        resposta = requests.put(
            _url_produto(produto_id, "liberar"),
            json={"quantidade": quantidade},
            headers={"X-Correlation-Id": correlation_id},
            timeout=TIMEOUT_SEGUNDOS,
        )
        resposta.raise_for_status()
    except requests.RequestException as erro:
        logger.error(
            "correlationId=%s Falha ao liberar %s unidades do produto %s: %s",
            correlation_id,
            quantidade,
            produto_id,
            erro,
        )
        return

    logger.info(
        "correlationId=%s Estoque do produto %s liberado (%s unidades)",
        correlation_id,
        produto_id,
        quantidade,
    )
