from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    class Config:
        env_file = ".env.test", ".env"
        env_file_encoding = "utf-8"

    telegram_token: str = Field(..., env="telegram_token")
    slack_token: str = Field(..., env="slack_token")

    app_url: str | None = Field(default=None, env="app_url")
    port: int = Field(default=8443, env="port")

    sentry_dsn: str | None = Field(env="sentry_dsn")
