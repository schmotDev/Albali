from pydantic import BaseSettings

class Settings(BaseSettings):
    VTIGER_URL: str
    VTIGER_USERNAME: str
    VTIGER_ACCESS_KEY: str

    WEBHOOK_SECRET: str

    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    MAX_RETRIES: int = 5

    class Config:
        env_file = ".env"

settings = Settings()
