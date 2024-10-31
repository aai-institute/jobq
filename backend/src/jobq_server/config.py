from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    AUTO_MIGRATE: bool = True
    """Automatically upgrade the database schema to the latest version"""

    DB_CONNECTION_STRING: str = "sqlite:///./jobq.db"
    """Database connection string"""


settings = Settings()
