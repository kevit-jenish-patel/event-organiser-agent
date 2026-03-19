from typing import Any, Dict, List

from pydantic import ValidationError

from repository.event.event_repository import event_repository
from tools.database.models import CreateEvent, EventQuery, UpdateEvent
from utils.logger import get_logger

logger = get_logger(__name__)

def get_all_events(query)->List[Dict[str,Any]]:
    """
    Retrieve a list of events from the database based on filter criteria.

    Description:
        This tool fetches multiple events from the database using the provided
        query filters. It returns a list of matching events. If no filters are
        provided (empty query), all events may be returned.

    Parameters:
        query (Dict[str, Any]):
            A dictionary containing filter criteria to search for events.
            The keys and values depend on the event schema and may include:
                - name (str, optional): Filter by event name
                - organiser (str, optional): Filter by organiser name
                - status (str, optional): Filter by event status
                - location (str, optional): Filter by event location
                - date (datetime or range, optional): Filter by event date

            Example:
                {
                    "status": "open",
                    "organiser": "John Doe"
                }

    Returns:
        List[Dict[str, Any]]:
            - On success:
                Returns a list of event objects. Each event is a dictionary containing:
                {
                    "_id": str,
                    "name": str,
                    "description": str,
                    "date": datetime,
                    "location": str,
                    "organiser": str,
                    "status": str,
                    ...
                }

                The list may be empty if no matching events are found.

            - On success (no matching events):
                Returns an empty list []

    Raises:
        ValidationError:
            Raised when the query is not a valid dictionary.

    LLM Usage Guidelines:
        - Always provide the query as a valid dictionary.
        - Use only known and valid fields when constructing the query.
        - Do not include unsupported or unknown keys.

        Handling Results:
        - If the function returns a non-empty list:
            → Present the list of events clearly to the user.
            → Optionally summarize or highlight relevant details.

        - If the function returns an empty list:
            → Inform the user that no matching events were found.
            → Suggest modifying or broadening the search criteria.

        - If a ValidationError occurs:
            → The query format is invalid.
            → Correct the query structure and retry the tool call.
            → Do NOT assume any results in this case.

    Notes:
        - This is a read-only operation and does not modify any data.
        - The filtering behavior depends on how the repository interprets the query.
        - Passing an empty query may return all events in the database.
    """
    try:
        if not isinstance(query,Dict):
            raise ValidationError("Query must be a dictionary")

        events = event_repository.get_all_events(
            query=query
        )
        return events
    except ValidationError as e:
        logger.exception(
            "Invalid query parameter",
            extra={"query":query}
        )
        raise e

def get_event_from_name(query: EventQuery)->Dict[str,Any]|None:
    """
    Retrieve an event from the database using query parameters.

    Description:
        This tool validates the input query and searches for an event in the database
        using the provided attributes (e.g., event name or other identifying fields).
        It returns the matching event if found.

    Parameters:
        query (EventQuery):
            A structured query object containing the fields required to identify
            an event. This must conform to the following EventQuery schema:
                - name (str)

    Returns:
        Dict[str, Any] | None:
            - On success (event found):
                Returns a dictionary containing event details such as:
                {
                    "_id": str,
                    "name": str,
                    "description": str,
                    "date": datetime,
                    "location": str,
                    "organiser": str,
                    "status": "open" | "full" | "closed" | "completed" | "cancelled",
                    ...
                }

            - On success (no event found):
                Returns None

    Raises:
        ValidationError:
            Raised when the input query does not match the expected schema.

    LLM Usage Guidelines:
        - Always provide a properly structured query matching the EventQuery schema.
        - If the function returns a valid dictionary:
            → Use the event data to answer the user's question.
        - If the function returns None:
            → Inform the user that no matching event was found.
            → Optionally ask for clarification or suggest similar queries.
        - If a ValidationError occurs:
            → The input format was incorrect.
            → Correct the query structure and retry the tool call.
            → Do NOT assume any result in this case.

    Notes:
        - This function does not modify any data; it is a read-only operation.
        - The search behavior depends on how EventQuery is defined and how the
          repository processes the query.
    """
    try:
        query = EventQuery.model_validate(query)

        event = event_repository.get_event_by_name(
            event_name=query.name
        )
        return event
    except ValidationError as e:
        logger.exception(
            "Invalid query parameter",
            extra={"query":query}
        )
        raise e


def create_event(event: CreateEvent)->bool:
    """
    Create a new event in the database.

    Description:
        This tool validates the provided event data and inserts a new event record
        into the database. It returns a boolean indicating whether the creation
        was successful.

    Parameters:
        event (CreateEvent):
            A structured object containing all required details to create an event.
            This must conform to the CreateEvent schema, which typically includes:
                - name (str): Name of the event
                - description (str): Description of the event
                - date (datetime): Date and time of the event
                - location (str): Event location
                - organiser (str): Organiser name
                - status ("open" | "full" | "closed" | "completed" | "cancelled"): Event status

    Returns:
        bool:
            - True:
                The event was successfully validated and inserted into the database.
            - False:
                The insertion failed (e.g., database did not return an inserted ID).

    Raises:
        ValidationError:
            Raised when the provided event data does not match the expected schema.

    LLM Usage Guidelines:
        - Always construct the event input strictly according to the CreateEvent schema.
        - Ensure all required fields are present and correctly typed before calling the tool.

        Handling Results:
        - If the function returns True:
            → Inform the user that the event was successfully created.
            → Optionally summarize the created event details.

        - If the function returns False:
            → Inform the user that the event creation failed.
            → Suggest retrying or checking input data.

        - If a ValidationError occurs:
            → The input format or data is incorrect.
            → Fix missing or invalid fields and retry the tool call.
            → Do NOT assume the event was created.

    Notes:
        - This function performs a write operation (creates new data).
        - It does not return the created event ID or object, only a success flag.
        - Ensure no duplicate or conflicting events are created unless intended.
    """
    try:
        event = CreateEvent.model_validate(event)
        inserted_id = event_repository.create_event(event.model_dump())

        success = True if inserted_id else False
        return success
    except ValidationError as e:
        logger.exception(
            "Invalid event parameter",
            extra={"event": event}
        )
        raise e


def update_event(query:EventQuery, event: UpdateEvent)->bool:
    """
    Update an existing event in the database.

    Description:
        This tool updates an existing event based on the provided query and update data.
        It first validates both the query (to identify the target event) and the event
        update payload, then applies the update in the database.

    Parameters:
        query (EventQuery):
            A structured object used to identify the event to be updated.
            This must conform to the following EventQuery schema:
                - name (str)

        event (UpdateEvent):
            A structured object containing the fields to update in the event.
            This must conform to the UpdateEvent schema and must include all
            the fields such as:
                - name (str): Name of the event
                - description (str): Description of the event
                - date (datetime): Date and time of the event
                - location (str): Event location
                - organiser (str): Organiser name
                - status ("open" | "full" | "closed" | "completed" | "cancelled"): Event status

    Returns:
        bool:
            - True:
                The event was successfully found and updated in the database.
            - False:
                No matching event was found OR the update operation did not modify any record.

    Raises:
        ValidationError:
            Raised when either the query or event update data does not match
            the expected schema.

    LLM Usage Guidelines:
        - Always construct both `query` and `event` inputs according to their respective schemas.
        - Ensure the query uniquely identifies the intended event.

        Handling Results:
        - If the function returns True:
            → Inform the user that the event was successfully updated.
            → Optionally summarize the updated fields.

        - If the function returns False:
            → Inform the user that no matching event was found OR no update was applied.
            → Suggest verifying the query or modifying the update fields.

        - If a ValidationError occurs:
            → The input structure or data is invalid.
            → Correct the query or update payload and retry the tool call.
            → Do NOT assume any update has occurred.

    Notes:
        - This is a write operation that modifies existing data.
        - The update is partial; only provided fields in `event` are modified.
        - Ensure that updates do not unintentionally overwrite important fields.
    """
    try:
        query = EventQuery.model_validate(query)
        event = UpdateEvent.model_validate(event)

        is_updated = event_repository.update_event_by_name(
            event_name=query.name,
            event=event.model_dump()
        )
        return is_updated
    except ValidationError as e:
        logger.exception(
            "Invalid query/event parameter",
            extra={"query": query,"event":event}
        )
        raise e

def delete_event_from_name(query: EventQuery)->bool:
    """
    Delete an event from the database using its name.

    Description:
        This tool validates the provided query and deletes an event that matches
        the given event name. The operation is permanent and cannot be undone.

    Parameters:
        query (EventQuery):
            A structured object used to identify the event to be deleted.
            This must conform to the EventQuery schema and must include:
                - name (str): The name of the event to delete

            Example:
                {
                    "name": "Tech Conference 2026"
                }

    Returns:
        bool:
            - True:
                The event was successfully found and deleted from the database.
            - False:
                No matching event was found, so no deletion was performed.

    Raises:
        ValidationError:
            Raised when the query does not match the expected schema
            (e.g., missing or invalid "name" field).

    LLM Usage Guidelines:
        - Always provide a valid query containing the event name.
        - Ensure the event name is accurate and specific.

        Handling Results:
        - If the function returns True:
            → Inform the user that the event has been successfully deleted.

        - If the function returns False:
            → Inform the user that no matching event was found.
            → Ask if they would like to try a different event name.

        - If a ValidationError occurs:
            → The input format is invalid.
            → Correct the query structure and retry the tool call.
            → Do NOT assume any deletion has occurred.

    Safety Guidelines:
        - Deletion is irreversible. Always confirm with the user before calling this tool.
        - Ensure the user explicitly intends to delete the event.

    Notes:
        - This is a destructive operation and permanently removes data.
        - The tool deletes events based solely on the event name.
        - Ensure there are no ambiguities in the event name before deletion.
    """
    try:
        query = EventQuery.model_validate(query)

        is_deleted = event_repository.delete_event_by_name(
            event_name=query.name
        )
        return is_deleted
    except ValidationError as e:
        logger.exception(
            "Invalid query parameter",
            extra={"query":query}
        )
        raise e
