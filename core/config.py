from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic.v1 import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(...,min_length=1)
    GOOGLE_API_KEY: str = Field(...,min_length=1)

    MONGODB_URI: str = Field(...,min_length=1)
    DATABASE_NAME: str = Field(...,min_length=1)

@lru_cache()
def get_settings():
    return Settings()
