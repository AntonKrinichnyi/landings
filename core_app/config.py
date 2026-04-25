from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str = "postgresql+asyncpg://app:app@localhost:5432"

    class Config:
        env_file = ".env"


settings = Settings()
