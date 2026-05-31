from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    subsamples: list[int] = Field(default=[1])
    db_path: str = Field(default="data/processed/cms.duckdb")
    raw_data_dir: str = Field(default="data/raw")
    manifests_dir: str = Field(default="data/manifests")
    ollama_base_url: str = Field(default="http://localhost:11434/v1")
    ollama_model: str = Field(default="llama3.2")
    log_level: str = Field(default="INFO")

    model_config = {"env_prefix": "CMS_", "env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
