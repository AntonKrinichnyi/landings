from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str = "postgresql+asyncpg://app:app@localhost:5432"
    secret_token: str = "realy_secret_token"
    jwt_algorithm: str = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()
