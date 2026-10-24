from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    TEST_DATABASE_URL: str | None = None
    # HS256 needs a key at least as long as the hash output (RFC 7518, 3.2).
    SECRET_KEY: str = Field(min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    OVERDUE_CHECK_INTERVAL: int = 60
    OVERDUE_WORKER_ENABLED: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
