import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    BOT_TOKEN: str
    API_KEY: str
    Exercise_API_KEY: str
    
    model_config = SettingsConfigDict(
        env_file=".env"
    )
    