from typing import List

from app.models.embedding_model import embed_model
from tools.database.models import CreateEvent

# --- Helper Function ---

def generate_event_embedding(event: CreateEvent) -> List[float]:
    """
    Combines the core semantic fields of an event and generates a vector embedding.
    Uses the globally configured LlamaIndex embedding model.
    """
    text_to_embed = (f"Event Name: {event.name}\nDescription: {event.description}\n"
                     f"Date: {event.date}\nLocation: {event.location}\n"
                     f"Organiser: {event.organiser}\nStatus: {event.status}")

    # embed_model is your configured model (e.g., OpenAIEmbedding or GoogleGenAIEmbedding)
    return embed_model.get_text_embedding(text_to_embed)
