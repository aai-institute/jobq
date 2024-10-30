from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_DSN: str = "sqlite:///./jobq.db"


settings = Settings()
