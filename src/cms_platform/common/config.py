from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_path: str = Field(default="data/processed/cms.duckdb")
    raw_data_dir: str = Field(default="data/raw")
    manifests_dir: str = Field(default="data/manifests")
    ollama_base_url: str = Field(default="http://localhost:11434/v1")
    ollama_model: str = Field(default="llama3.2")
    log_level: str = Field(default="INFO")
    # Pre-generated 1 000-patient Synthea CSV dataset from MITRE.
    # TODO(future-source): swap for Blue Button 2.0 FHIR API once OAuth registration
    #   is in place — see ARCHITECTURE.md "Real Data Migration Path".
    synthea_data_url: str = Field(
        default=(
            "https://synthetichealth.github.io/synthea-sample-data"
            "/downloads/synthea_sample_data_csv_latest.zip"
        )
    )

    model_config = SettingsConfigDict(env_prefix="CMS_", env_file=".env", extra="ignore")


def get_settings() -> Settings:
    return Settings()
