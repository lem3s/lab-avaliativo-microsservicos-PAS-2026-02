from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import configuracoes

engine = create_engine(configuracoes.database_url, pool_pre_ping=True)
SessaoLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def obter_sessao():
    with SessaoLocal() as sessao:
        yield sessao
