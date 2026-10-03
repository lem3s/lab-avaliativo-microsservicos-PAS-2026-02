import logging

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.banco import obter_sessao
from app.esquemas import Mensagem, ProdutoSaida, QuantidadeEntrada
from app.modelos import Produto

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/produtos", tags=["produtos"])

RESPOSTA_404 = {404: {"model": Mensagem}}


def produto_inexistente() -> JSONResponse:
    return JSONResponse(status_code=404, content={"mensagem": "Produto inexistente"})


@router.get("", response_model=list[ProdutoSaida])
def listar_produtos(sessao: Session = Depends(obter_sessao)):
    return sessao.scalars(select(Produto).order_by(Produto.id)).all()


@router.get("/{produto_id}", response_model=ProdutoSaida, responses=RESPOSTA_404)
def buscar_produto(produto_id: int, sessao: Session = Depends(obter_sessao)):
    produto = sessao.get(Produto, produto_id)
    if produto is None:
        return produto_inexistente()
    return produto


@router.put(
    "/{produto_id}/reservar",
    response_model=ProdutoSaida,
    responses={**RESPOSTA_404, 409: {"model": Mensagem}},
)
def reservar_estoque(
    produto_id: int,
    entrada: QuantidadeEntrada,
    sessao: Session = Depends(obter_sessao),
    x_correlation_id: str | None = Header(default=None),
):
    produto = sessao.scalars(
        update(Produto)
        .where(Produto.id == produto_id, Produto.quantidade >= entrada.quantidade)
        .values(quantidade=Produto.quantidade - entrada.quantidade)
        .returning(Produto)
    ).one_or_none()

    if produto is None:
        sessao.rollback()
        if sessao.get(Produto, produto_id) is None:
            logger.warning("correlationId=%s Produto %s inexistente", x_correlation_id, produto_id)
            return produto_inexistente()
        logger.warning(
            "correlationId=%s Estoque insuficiente para o produto %s (solicitado %s)",
            x_correlation_id,
            produto_id,
            entrada.quantidade,
        )
        return JSONResponse(status_code=409, content={"mensagem": "Estoque insuficiente"})

    sessao.commit()
    logger.info("correlationId=%s Produto %s reservado", x_correlation_id, produto_id)
    return produto


@router.put("/{produto_id}/liberar", response_model=ProdutoSaida, responses=RESPOSTA_404)
def liberar_estoque(
    produto_id: int,
    entrada: QuantidadeEntrada,
    sessao: Session = Depends(obter_sessao),
    x_correlation_id: str | None = Header(default=None),
):
    produto = sessao.scalars(
        update(Produto)
        .where(Produto.id == produto_id)
        .values(quantidade=Produto.quantidade + entrada.quantidade)
        .returning(Produto)
    ).one_or_none()

    if produto is None:
        sessao.rollback()
        logger.warning("correlationId=%s Produto %s inexistente", x_correlation_id, produto_id)
        return produto_inexistente()

    sessao.commit()
    logger.info(
        "correlationId=%s Produto %s liberado (%s unidades)",
        x_correlation_id,
        produto_id,
        entrada.quantidade,
    )
    return produto
