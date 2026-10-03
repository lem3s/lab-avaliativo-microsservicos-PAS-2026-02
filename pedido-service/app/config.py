from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    database_url: str = "postgresql+psycopg://pedido:pedido@localhost:5432/pedido"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    estoque_service_url: str = "http://localhost:8081"
    simular_falha_apos_reserva: bool = False
    compensacao_habilitada: bool = True


configuracoes = Configuracoes()
