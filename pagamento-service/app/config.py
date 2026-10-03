from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    database_url: str = "postgresql+psycopg://pagamento:pagamento@localhost:5432/pagamento"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    taxa_aprovacao: float = 0.8
    pagamento_falhar_pedido_id: int | None = None


configuracoes = Configuracoes()
