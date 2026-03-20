from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo.operations import SearchIndexModel

from db.config import MongoManager
from utils.constants import EMBEDDING_DIMENSIONS
from utils.logger import get_logger

logger = get_logger(__name__)


class EventRepository:
    def __init__(self):
        self.collection = MongoManager.get_db()["events"]
        # The name of the Vector Search Index created in the MongoDB Atlas UI
        self.vector_index_name = "event_vector_index"
        self.index_exists = False

    def _ensure_vector_index_exists(self):
        """
        Checks if the Atlas Vector Search index exists, and creates it if it does not.
        """
        try:
            if self.index_exists:
                return

            # 1. Fetch existing search indexes
            existing_indexes = list(self.collection.list_search_indexes())
            index_names = [idx.get("name") for idx in existing_indexes]

            # 2. Check if our index is already there
            if self.vector_index_name in index_names:
                self.index_exists = True
                logger.info(f"Vector search index '{self.vector_index_name}' already exists. Skipping creation.")
                return

            logger.info(f"Creating vector search index '{self.vector_index_name}'...")

            # 3. Define the Vector Search Index schema
            search_index_model = SearchIndexModel(
                definition={
                    "fields": [
                        {
                            "type": "vector",
                            "path": "embedding",
                            "numDimensions": EMBEDDING_DIMENSIONS,
                            "similarity": "cosine"  # 'cosine', 'euclidean', or 'dotProduct'
                        }
                    ]
                },
                name=self.vector_index_name,
                type="vectorSearch"  # CRITICAL: Must specify it's a vector search, not standard text search
            )

            # 4. Create the index
            self.collection.create_search_index(model=search_index_model)
            self.index_exists = True
            logger.info(f"Successfully triggered creation of vector search index: {self.vector_index_name}")

            # Note: Atlas builds these indexes asynchronously in the background.
            # It may take a minute before semantic_search returns results for newly inserted data.

        except Exception:
            self.index_exists = False
            logger.exception("Failed to create vector search index")

    def get_all_events(self, query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        query = query or {}
        cursor = self.collection.find(query)
        events = list(cursor)
        for event in events:
            event["_id"] = str(event["_id"])
        return events

    def get_event(self, query: Dict[str, Any]) -> Dict[str, Any] | None:
        event = self.collection.find_one(query)
        if event:
            event["_id"] = str(event["_id"])
        return event

    def get_event_by_name(self, event_name: str) -> Dict[str, Any] | None:
        return self.get_event(query={"name": event_name})

    def create_event(self, event_data: Dict[str, Any], embedding: List[float]) -> str:
        """
        Inserts a new event along with its generated vector embedding.
        """
        event_data["createdAt"] = datetime.now(timezone.utc)
        event_data["embedding"] = embedding

        result = self.collection.insert_one(event_data)
        return str(result.inserted_id)

    def update_event(self, query: Dict[str, Any], event_data: Dict[str, Any],
                     new_embedding: Optional[List[float]] = None) -> bool:
        """
        Safely applies a partial update to an event. Conditionally updates the embedding
        if fields that affect semantics (like name or description) were changed.
        """
        if not event_data and not new_embedding:
            return False  # Failsafe: nothing to update

        event_data["updatedAt"] = datetime.now(timezone.utc)

        if new_embedding:
            event_data["embedding"] = new_embedding

        result = self.collection.update_one(
            query,
            {"$set": event_data}
        )
        return result.modified_count > 0

    def update_event_by_name(
            self,
            event_name: str,
            event_data: Dict[str, Any],
            new_embedding: Optional[List[float]] = None
    ) -> bool:
        return self.update_event(
            query={"name": event_name},
            event_data=event_data,
            new_embedding=new_embedding
        )

    def delete_event_by_name(self, event_name: str) -> bool:
        result = self.collection.delete_one({"name": event_name})
        return result.deleted_count > 0

    def semantic_search(self, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Performs a semantic search using MongoDB Atlas Vector Search.
        """
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.vector_index_name,
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": limit * 10,  # Atlas recommendation for recall accuracy
                    "limit": limit
                }
            },
            {
                # Step 2: Add the relevance score to the document
                "$set": {
                    "score": {"$meta": "vectorSearchScore"}
                }
            },
            {
                # Step 3: Remove the heavy vector array from the results
                "$unset": "embedding"
            }
        ]

        try:
            cursor = self.collection.aggregate(pipeline)
            events = list(cursor)
            for event in events:
                event["_id"] = str(event["_id"])
            return events
        except Exception as e:
            logger.exception("Semantic search failed. Verify your MongoDB Atlas Vector Index is configured properly.")
            raise e


event_repository = EventRepository()
