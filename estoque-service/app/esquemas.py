from pydantic import BaseModel, ConfigDict, PositiveInt


class ProdutoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    quantidade: int


class QuantidadeEntrada(BaseModel):
    quantidade: PositiveInt


class Mensagem(BaseModel):
    mensagem: str
