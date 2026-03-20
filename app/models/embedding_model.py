from google.genai.types import EmbedContentConfig
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

from core.config import get_settings
from utils.constants import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL

settings = get_settings()

# Initialize embedding model
embed_model = GoogleGenAIEmbedding(
    model_name=EMBEDDING_MODEL,
    api_key=settings.GOOGLE_API_KEY,
    embedding_config=EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONS)
)
