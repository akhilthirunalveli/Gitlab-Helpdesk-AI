import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

try:
    texts = ["hello", "world"]
    contents = [types.Content(parts=[types.Part.from_text(text=t)]) for t in texts]
    response = client.models.embed_content(
        model="gemini-embedding-2",
        contents=contents
    )
    print("Type of response.embeddings:", type(response.embeddings))
    print("Length of response.embeddings:", len(response.embeddings))
    if hasattr(response.embeddings[0], 'values'):
        print("Length of first embedding values:", len(response.embeddings[0].values))
    else:
        print("First embedding:", response.embeddings[0])
except Exception as e:
    print("Error:", e)
