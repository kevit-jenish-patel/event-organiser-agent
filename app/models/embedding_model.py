from google.genai.types import EmbedContentConfig
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

from core.config import get_settings

settings = get_settings()

# Initialize embedding model
embed_model = GoogleGenAIEmbedding(
    model_name="gemini-embedding-001", # gemini-embedding-2-preview
    api_key=settings.GOOGLE_API_KEY,
    embedding_config=EmbedContentConfig(output_dimensionality=1536)
)
