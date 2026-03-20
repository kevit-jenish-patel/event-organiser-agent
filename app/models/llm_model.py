from llama_index.llms.google_genai import GoogleGenAI

from core.config import get_settings
from utils.constants import LLM_MODEL

settings = get_settings()

llm = GoogleGenAI(
    model=LLM_MODEL,
    api_key=settings.GOOGLE_API_KEY,
    temperature=0.0,
)

# llm = OpenAI(
#     model="gpt-3.5-turbo",
#     api_key=settings.OPENAI_API_KEY,
#     temperature=0.5
# )
