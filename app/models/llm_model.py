from llama_index.llms.google_genai import GoogleGenAI

from core.config import get_settings

settings = get_settings()

llm = GoogleGenAI(
    model="gemini-2.5-flash",
    api_key=settings.GOOGLE_API_KEY,
    temperature=0.0,
)

# llm = OpenAI(
#     model="gpt-3.5-turbo",
#     api_key=settings.OPENAI_API_KEY,
#     temperature=0.5
# )
