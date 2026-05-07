from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BCQT Showcase"
    app_env: str = "dev"
    database_url: str = "sqlite:///./data/bcqt.sqlite"
    secret_key: str = "dev-only-change-me"
    # Default cho dev local; production override qua env SOURCE_DATA_DIR.
    source_data_dir: Path = Path("./_source_data")
    settlement_version: str = "v12.0"


settings = Settings()
