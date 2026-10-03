from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.banco import Base


class Produto(Base):
    __tablename__ = "produto"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    quantidade: Mapped[int]
