from pydantic import BaseModel


class Settings(BaseModel):
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql://la_traffic:la_traffic@localhost:5432/la_traffic"


settings = Settings()
