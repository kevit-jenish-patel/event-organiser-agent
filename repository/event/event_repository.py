from datetime import datetime, timezone
from typing import Any, Dict, List

from bson import ObjectId

from db.config import MongoManager


class EventRepository:
    def __init__(self):
        self.collection = MongoManager.get_db()["events"]

    def get_all_events(self, query: Dict[str,Any])->List[Dict[str,Any]]:
        cursor = self.collection.find(query)

        events = cursor.to_list(length=None)
        for event in events:
            event["_id"] = str(event["_id"])

        return events

    def get_event(self, query: Dict[str,Any])->Dict[str,Any]|None:
        event = self.collection.find_one(query)
        event["_id"] = str(event["_id"])
        return event

    def get_event_by_id(self, event_id: str)->Dict[str,Any]|None:
        return self.get_event(query={"_id": ObjectId(event_id)})

    def get_event_by_name(self, event_name: str)->Dict[str,Any]|None:
        return self.get_event(query={"name": event_name})

    def create_event(self, event: Dict[str,Any]) -> str:
        event["createdAt"] = datetime.now(timezone.utc)

        result= self.collection.insert_one(event)

        return str(result.inserted_id)

    def update_event(self, query: Dict[str,Any], event: Dict[str,Any])->bool:
        event["updatedAt"] = datetime.now(timezone.utc)

        result = self.collection.update_one(
            query,
            {"$set": event}
        )

        return result.modified_count > 0

    def update_event_by_id(self, event_id: str, event: Dict[str,Any])->bool:
        return self.update_event(
            query={"_id": ObjectId(event_id)},
            event=event
        )

    def update_event_by_name(self, event_name: str, event: Dict[str,Any])->bool:
        return self.update_event(
            query={"name": event_name},
            event=event
        )

    def delete_event(self, query: Dict[str,Any])->bool:
        result = self.collection.delete_one(query)

        return result.deleted_count > 0

    def delete_event_by_id(self, event_id: str)->bool:
        return self.delete_event(
            query={"_id": ObjectId(event_id)}
        )

    def delete_event_by_name(self, event_name: str)->bool:
        return self.delete_event(
            query={"name": event_name}
        )

event_repository = EventRepository()
