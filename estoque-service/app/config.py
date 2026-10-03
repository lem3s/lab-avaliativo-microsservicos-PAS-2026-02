from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    database_url: str = "postgresql+psycopg://estoque:estoque@localhost:5432/estoque"


configuracoes = Configuracoes()
