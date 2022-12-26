from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    class Config:
        env_file = ".env.test", ".env"
        env_file_encoding = "utf-8"

    telegram_token: str = Field(..., env="telegram_token")
    slack_token: str = Field(..., env="slack_token")

    app_url: str | None = Field(default=None, env="app_url")
    port: int = Field(default=8443, env="port")

    request_connection_pool_size: int = 8
    request_read_timeout: int = 10
    request_write_timeout: int = 30
    request_connect_timeout: int = 10
    request_pool_timeout: int = 30

    sentry_dsn: str | None = Field(env="sentry_dsn")
