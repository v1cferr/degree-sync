from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ava_user: str
    ava_pass: str

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
