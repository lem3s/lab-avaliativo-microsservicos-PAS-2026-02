from enum import StrEnum

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.banco import Base


class StatusPagamento(StrEnum):
    APROVADO = "APROVADO"
    REJEITADO = "REJEITADO"


class Pagamento(Base):
    __tablename__ = "pagamento"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pedido_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    status: Mapped[str] = mapped_column(String(50))
    correlation_id: Mapped[str] = mapped_column(String(36))
