
from db.config import SQLiteManager
from utils.logger import get_logger

logger = get_logger(__name__)


class UserRepository:
    def __init__(self):
        self.db = SQLiteManager.get_db()

user_repository = UserRepository()
