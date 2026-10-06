# Laboratório de Microsserviços — PAS 2026/2
**Alunos: João Victor Lemes Faria; Yasmin Lopes de Moura**  

- **Parte 1** — [Diagrama da arquitetura](docs/arquitetura.drawio.png)
- **Parte 2** — [Código-fonte dos serviços](#estrutura)
- **Parte 3** — [docker-compose.yml](docker-compose.yml)
- **Parte 4** — [Prints (criação do pedido, reserva de estoque, publicação da mensagem, processamento do pagamento)](docs/evidencias/)
- **Parte 5** — [Respostas das perguntas](RESPOSTAS.md)

Plataforma de e-commerce composta por três microsserviços em Python (FastAPI + Pydantic, gerenciados com uv),
cada um com seu próprio PostgreSQL, comunicando-se via REST e RabbitMQ.

| Serviço | Responsabilidade | Porta (host) | Banco |
|---|---|---|---|
| `estoque-service` | Consulta e reserva de estoque | 8081 | `estoque-db` |
| `pedido-service` | Criação e consulta de pedidos | 8080 | `pedido-db` |
| `pagamento-service` | Processamento assíncrono de pagamentos | — | `pagamento-db` |
| `rabbitmq` | Broker de mensagens | 5672 / 15672 (painel) | — |

Diagrama arquitetural: [`docs/arquitetura.md`](docs/arquitetura.md)

## Estrutura

```
├── estoque-service/
│   ├── app/                 código (FastAPI)
│   ├── estoque-db/          SQL de criação e dados iniciais
│   ├── Dockerfile
│   └── pyproject.toml / uv.lock
├── pedido-service/          (mesma estrutura + clientes/ e mensageria/)
├── pagamento-service/       (worker, sem API HTTP)
├── docker-compose.yml
└── docs/
```

## Pré-requisitos

- Docker com Docker Compose v2
- cURL (ou Postman / Insomnia)
- Opcional, para desenvolvimento local: [uv](https://docs.astral.sh/uv/)

## Execução

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f
```

- Swagger do Estoque: http://localhost:8081/docs
- Swagger do Pedido: http://localhost:8080/docs
- Painel do RabbitMQ: http://localhost:15672 (usuário `guest`, senha `guest`)

Para parar: `docker compose down`. Para apagar também os bancos e voltar aos dados iniciais: `docker compose down -v`.

> Os scripts SQL de cada `<servico>-db/` só são executados quando o volume do banco é criado.
> Após alterar um SQL, rode `docker compose down -v`.

## Variáveis de ambiente

Definidas no `docker-compose.yml`. As de simulação de falha podem ser passadas na linha de comando.

| Variável | Serviço | Padrão | Uso |
|---|---|---|---|
| `DATABASE_URL` | todos | — | conexão com o banco do próprio serviço |
| `RABBITMQ_URL` | pedido, pagamento | — | conexão com o RabbitMQ |
| `ESTOQUE_SERVICE_URL` | pedido | `http://estoque-service:8000` | URL do Estoque |
| `SIMULAR_FALHA_APOS_RESERVA` | pedido | `false` | lança erro após reservar estoque e antes de salvar o pedido |
| `COMPENSACAO_HABILITADA` | pedido | `true` | libera o estoque quando a criação do pedido falha |
| `PAGAMENTO_FALHAR_PEDIDO_ID` | pagamento | vazio | força falha no processamento do pedido com esse id |

## Endpoints

### Estoque Service (`localhost:8081`)

| Método | Rota | Respostas |
|---|---|---|
| GET | `/produtos` | 200 |
| GET | `/produtos/{id}` | 200, 404 |
| PUT | `/produtos/{id}/reservar` `{"quantidade": n}` | 200, 404 `Produto inexistente`, 409 `Estoque insuficiente` |
| PUT | `/produtos/{id}/liberar` `{"quantidade": n}` | 200, 404 |

### Pedido Service (`localhost:8080`)

| Método | Rota | Respostas |
|---|---|---|
| POST | `/pedidos` `{"produtoId": 1, "quantidade": 2}` | 201, 404, 409, 500, 503 |
| GET | `/pedidos` | 200 |
| GET | `/pedidos/{id}` | 200, 404 |

## Mensageria

| Exchange (direct) | Fila (quorum) | Routing key | Produtor → Consumidor |
|---|---|---|---|
| `pedidos.exchange` | `pedido.criado` | `pedido.criado` | Pedido → Pagamento |
| `pagamentos.exchange` | `pagamento.processado` | `pagamento.processado` | Pagamento → Pedido |

As filas têm `x-delivery-limit=3`: depois de 3 reentregas com falha, a mensagem vai para a DLQ correspondente
(`pedido.criado.dlq` / `pagamento.processado.dlq`).