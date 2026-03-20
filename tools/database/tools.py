import json
from typing import Any, Dict, List, Optional

from llama_index.core.workflow import Context, HumanResponseEvent, InputRequiredEvent
from pydantic import ValidationError

from app.models.embedding_model import embed_model
from repository.event.event_repository import event_repository
from tools.database.models import CreateEvent, EventQuery, UpdateEvent
from utils.helpers import generate_event_embedding
from utils.logger import get_logger

logger = get_logger(__name__)

# --- LlamaIndex Tools ---

def search_events(query: str) -> List[Dict[str, Any]]:
    """
    Perform a semantic search to find events based on a natural language query.

    Description:
        This tool uses vector embeddings to perform a similarity search in the database.
        Unlike traditional exact-match filtering, it understands context, synonyms, and
        semantic meaning. Use this tool as your primary method whenever a user asks to
        find, list, or inquire about existing events.

    Parameters:
        query (str):
            A clear, natural language string representing the user's search intent.
            You should actively formulate this query based on the user's request, combining
            relevant keywords like topics, locations, or timeframes into a single sentence.
            Example: "Artificial Intelligence conferences in Mumbai next month"

    Returns:
        List[Dict[str, Any]]:
            - On success (events found):
                Returns a list of up to 5 event dictionaries sorted by relevance.
                Each dictionary contains the event details and a similarity score:
                {
                    "_id": str,
                    "name": str,
                    "description": str,
                    "date": str (ISO 8601 UTC format),
                    "location": str,
                    "organiser": str,
                    "status": str,
                    "score": float (Relevance metric)
                }

            - On success (no events found) or failure:
                Returns an empty list: []

    LLM Usage Guidelines:
        - Tool Selection: Always default to this tool for retrieving events unless the
          user is explicitly asking to create, update or delete a specific event.
        - Query Optimization: Translate vague user requests into rich search strings.
          If a user says "tech stuff", expand the query to "technology events, meetups, or conferences".
        - Handling Results:
            → If events are returned: Synthesize the results into a friendly, conversational
              response. Highlight the most relevant events and their key details (date, location).
            → If an empty list [] is returned: Politely inform the user that no matching
              events were found. Suggest they try different keywords or broaden their search.
    """
    try:
        query_embedding = embed_model.get_text_embedding(query)
        events = event_repository.semantic_search(query_vector=query_embedding, limit=5)
        return events
    except Exception:
        logger.exception("Failed to execute semantic search", extra={"query": query})
        return []


def create_event(event: CreateEvent) -> bool:
    """
    Create a new event in the database.

    Description:
        This tool validates the provided event data, generates a semantic vector embedding
        for future natural language searchability, and inserts the new event record into MongoDB.
        Use this tool whenever a user explicitly requests to schedule, host, or create a new event.

    Parameters:
        event (CreateEvent):
            A structured object containing all required details to create an event.
            You must construct this object using the following exact schema:
                - name (str): The exact, official name of the event.
                - description (str): A clear, brief description of the event's purpose or agenda.
                - date (str): The date and time of the event.
                  CRITICAL: This must be strictly in ISO 8601 UTC format (e.g., '2026-04-15T15:00:00Z').
                  CRITICAL: The date MUST be in the future relative to the current time provided in your system prompt.
                - location (str): The physical venue or virtual link for the event.
                - organiser (str): The name of the person or entity hosting the event.
                - status (str): The initial status of the event. Must be exactly one of:
                  'open', 'full', 'closed', 'completed', or 'cancelled'. (Defaults to 'open').

    Returns:
        bool:
            - True: The event was successfully validated, embedded, and inserted into the database.
            - False: The insertion failed at the database level.
            - Raises ValidationError: If the input data is malformed or the date is in the past.

    LLM Usage Guidelines:
        - Time Awareness: Before calling this tool, always check the user's requested date
          against the current time provided in your system context. If the user asks for a
          date in the past, DO NOT call this tool. Inform the user that events must be scheduled in the future.
        - Data Inference: If the user request is missing required fields (e.g., they provide
          a name and date, but no location or organiser), politely ask them to provide the
          missing details before executing the tool. Do not hallucinate missing data.
        - Handling Results:
            → If True: Enthusiastically confirm to the user that the event has been successfully created
              and summarize the key details (Name, Date, Location) back to them.
            → If a ValidationError occurs: Read the error message carefully. If it's a date issue,
              ask the user to clarify the correct future date. If it's a format issue, silently fix
              your JSON payload and retry.
    """
    try:
        event_data = CreateEvent.model_validate(event)

        # 1. Generate the embedding
        embedding = generate_event_embedding(event=event_data)

        # 2. Insert into database
        inserted_id = event_repository.create_event(
            event_data=event_data.model_dump(),
            embedding=embedding
        )
        return bool(inserted_id)

    except ValidationError as e:
        logger.exception("Invalid event parameter", extra={"event": event})
        raise e


async def update_event(ctx: Context, query: EventQuery, event: UpdateEvent) -> str:
    """
    Update an existing event in the database.

    Description:
        This tool applies a partial update to an existing event. It conditionally recalculates
        and updates the semantic vector embedding if fields like name, description, date,
        location, organiser, or status are modified. Because this modifies database records,
        this tool inherently triggers a security interceptor that pauses execution to ask the
        human user for explicit approval before writing to the database.

    Parameters:
        ctx (Context): The internal workflow context.

        query (EventQuery):
            A structured object identifying the exact event to update.
                - name (str): The current, exact name of the event in the database.

        event (UpdateEvent):
            A structured object containing ONLY the fields that need to be updated.
            All fields in this schema are optional.
                - name (str, optional): The new name of the event.
                - description (str, optional): The new description.
                - date (str, optional): The new date strictly in ISO 8601 UTC format.
                - location (str, optional): The new location/venue.
                - organiser (str, optional): The new organiser name.
                - status (str, optional): The new status ('open', 'full', 'closed', 'completed', 'cancelled').

    Returns:
        str: A descriptive message indicating the result of the operation.
            - "Success: Successfully updated the event."
            - "Failed: No fields provided to update."
            - "Failed: The human user denied permission to execute this database action."
            - "Failed: Event not found."
            - "Failed: Database could not update the event."

    LLM Usage Guidelines:
        - Exact Match Requirement: You must know the EXACT current name of the event to populate
          the `query` parameter. If the user's request is vague (e.g., "Update the AI meetup"),
          use the `search_events` tool FIRST to find the exact event name before calling this tool.
        - The Partial Update Rule (CRITICAL): ONLY populate the fields in the `UpdateEvent` schema
          that the user explicitly asked to change. Leave all other fields empty/null. Do not fetch
          and pass existing data back into this tool just to fill out the schema.
        - Handling Human Rejection: If the tool returns the message stating the human denied
          permission, DO NOT apologize as if it is an error. Acknowledge that the user cancelled
          the update and ask what they would like to do next.
        - Date Updates: If updating the date, ensure it is in the future relative to the system's
          current time, just like when creating an event.
    """
    try:
        query_data = EventQuery.model_validate(query)
        update_payload = UpdateEvent.model_validate(event)

        # exclude_unset=True ensures we only update the fields the user explicitly changed
        update_dict = update_payload.model_dump(exclude_unset=True)

        if not update_dict:
            return "Failed: No fields provided to update."

        payload = {"query": query_data.model_dump(), "update": update_dict}
        prefix = (f"\n\n⚠️ [SECURITY INTERCEPTOR] The AI wants to update an event.\n"
                  f"📄 Payload: {json.dumps(payload, indent=2, default=str)}\n"
                  f"Approve this update? (y/n): ")

        # Suspend tool execution and emit an event to the main stream
        human_response = await ctx.wait_for_event(
            HumanResponseEvent,
            waiter_id="update_event_confirmation",
            waiter_event=InputRequiredEvent(prefix=prefix,user_name="human"),
            requirements={"user_name": "human"},
        )

        # Evaluate human input
        if human_response.response.strip().lower() not in ["y", "yes"]:
            return "Failed: The human user denied permission to execute this database action."

        print("\n✅ Action approved. Executing...", flush=True)

        new_embedding: Optional[List[float]] = None

        # Check if any fields that affect the semantic search were modified
        semantic_fields = {"name", "description", "location", "date", "organiser", "status"}
        if any(field in update_dict for field in semantic_fields):

            # Fetch the existing event to merge old and new data for an accurate embedding
            existing_event = event_repository.get_event_by_name(event_name=query_data.name)
            if not existing_event:
                return "Failed: Event not found."

            merged_name = update_dict.get("name", existing_event.get("name", ""))
            merged_desc = update_dict.get("description", existing_event.get("description", ""))
            merged_loc = update_dict.get("location", existing_event.get("location", ""))
            merged_date = update_dict.get("date", existing_event.get("date", ""))
            merged_organiser = update_dict.get("organiser", existing_event.get("organiser", ""))
            merged_status = update_dict.get("status", existing_event.get("status", ""))
            merged_event = CreateEvent(
                name=merged_name,
                description=merged_desc,
                date=merged_date,
                location=merged_loc,
                organiser=merged_organiser,
                status=merged_status
            )

            new_embedding = generate_event_embedding(merged_event)

        # Apply the update
        success = event_repository.update_event_by_name(
            event_name=query_data.name,
            event_data=update_dict,
            new_embedding=new_embedding
        )

        return "Success: Successfully updated the event." if success else "Failed: Database could not update the event."
    except ValidationError as e:
        logger.exception("Invalid query/event parameter", extra={"query": query, "event": event})
        raise e

async def delete_event(ctx: Context, query: EventQuery) -> str:
    """
    Delete an event from the database permanently using its exact name.

    Description:
        This tool permanently removes an event record from the database. Because this is a
        destructive operation, it inherently triggers a mandatory security interceptor that
        pauses execution to ask the human user for explicit Y/N approval before actually
        deleting the data. Use this tool whenever a user explicitly requests to cancel,
        remove, or delete an event.

    Parameters:
        ctx (Context): The internal workflow context. (Injected automatically by the system).

        query (EventQuery):
            A structured object identifying the exact event to be deleted.
                - name (str): The exact, current name of the event in the database.

    Returns:
        str: A descriptive message indicating the result of the operation.
            - "Success: Successfully deleted the event."
            - "Failed: The human user denied permission to execute this database action."
            - "Failed: Event not found."

    LLM Usage Guidelines:
        - Exact Match Requirement: You must know the EXACT current name of the event to populate
          the `query` parameter. If the user's request is vague (e.g., "Delete that tech meetup"),
          you MUST use the `search_events` tool FIRST to find the exact event name before calling this tool.
        - Automatic Confirmation: Do NOT ask the user "Are you sure you want to delete this?"
          in your conversational response. The tool itself will automatically freeze the terminal
          and prompt the user for secure confirmation. Simply execute the tool when requested.
        - Handling Human Rejection: If the tool returns the message stating the human denied
          permission, DO NOT treat it as a system error or apologize. Simply acknowledge that
          the deletion was cancelled by the user and ask how else you can help.
        - Handling Not Found: If the tool returns "Failed: Event not found.", inform the user
          and suggest using the search tool to find the correct event name.
    """
    try:
        query_data = EventQuery.model_validate(query)

        # --- NATIVE HITL INTERCEPTION ---
        prefix = (f"\n\n⚠️ [SECURITY INTERCEPTOR] "
                  f"The AI wants to PERMANENTLY DELETE the event: '{query_data.name}'.\n"
                  f"Approve this deletion? (y/n): ")

        human_response = await ctx.wait_for_event(
            HumanResponseEvent,
            waiter_id="delete_event_confirmation",
            waiter_event=InputRequiredEvent(prefix=prefix, user_name="human"),
            requirements={"user_name": "human"},
        )

        # Evaluate human input
        if human_response.response.strip().lower() not in ["y", "yes"]:
            return "Failed: The human user denied permission to execute this database action."

        print("\n✅ Action approved. Executing...", flush=True)

        success = event_repository.delete_event_by_name(event_name=query_data.name)
        return "Success: Successfully deleted the event." if success else "Failed: Event not found."
    except ValidationError as e:
        logger.exception("Invalid query parameter", extra={"query": query})
        raise e
