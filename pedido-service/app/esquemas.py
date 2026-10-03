from typing import Literal

from pydantic import BaseModel, ConfigDict, PositiveInt
from pydantic.alias_generators import to_camel

from app.modelos import StatusPedido


class EsquemaBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, from_attributes=True)


class PedidoEntrada(EsquemaBase):
    produto_id: int
    quantidade: PositiveInt


class PedidoSaida(EsquemaBase):
    id: int
    produto_id: int
    quantidade: int
    status: StatusPedido
    correlation_id: str


class Mensagem(BaseModel):
    mensagem: str


class PedidoCriadoEvento(EsquemaBase):
    pedido_id: int
    produto_id: int
    quantidade: int
    correlation_id: str


class PagamentoProcessadoEvento(EsquemaBase):
    pedido_id: int
    status: Literal["APROVADO", "REJEITADO"]
    correlation_id: str
