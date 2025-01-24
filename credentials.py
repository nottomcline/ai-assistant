from decouple import config as environ  # type: ignore

# Your OpenAI API Key
OPENAI_API_KEY = str(environ("OPENAI_API_KEY", ""))