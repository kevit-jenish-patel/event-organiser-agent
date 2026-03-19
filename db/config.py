from typing import Optional

from pymongo import MongoClient

from core.config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

class MongoManager:
    _client: Optional[MongoClient] = None

    @classmethod
    def _get_client(cls) -> MongoClient:
        if cls._client is None:
            cls._client = MongoClient(
                settings.MONGODB_URI,
                maxPoolSize=20,
                serverSelectionTimeoutMS=5000
            )
        return cls._client

    @classmethod
    def get_db(cls):
        try:
            return cls._get_client()[settings.DATABASE_NAME]
        except Exception:
            logger.exception("Failed to connect to database")

    @classmethod
    def close(cls):
        if cls._client:
            cls._client.close()
            cls._client = None
