import os
from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY")
print("GEMINI_API_KEY in environment:", api_key)

if api_key:
    client = genai.Client(api_key=api_key)
else:
    print("No GEMINI_API_KEY found in environment. Attempting to use default configuration.")
    client = None

try:
    res = client.models.embed_content(
        model="models/gemini-embedding-001",
        contents="hello",
        config=types.EmbedContentConfig(task_type="retrieval_document")
    )
    print("Success! Embedding length:", len(res.embeddings[0].values))
except Exception as e:
    print("Failed to call Gemini API:", str(e))
