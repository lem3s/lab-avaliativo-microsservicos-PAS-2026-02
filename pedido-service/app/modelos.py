from enum import StrEnum

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.banco import Base


class StatusPedido(StrEnum):
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    PAGO = "PAGO"
    REJEITADO = "REJEITADO"


class Pedido(Base):
    __tablename__ = "pedido"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    produto_id: Mapped[int] = mapped_column(BigInteger)
    quantidade: Mapped[int]
    status: Mapped[str] = mapped_column(String(50))
    correlation_id: Mapped[str] = mapped_column(String(36))
