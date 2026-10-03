from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.modelos import StatusPagamento


class EsquemaBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)


class PedidoCriadoEvento(EsquemaBase):
    pedido_id: int
    produto_id: int
    quantidade: int
    correlation_id: str


class PagamentoProcessadoEvento(EsquemaBase):
    pedido_id: int
    status: StatusPagamento
    correlation_id: str
