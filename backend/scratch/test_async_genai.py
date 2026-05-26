import os
import asyncio
from google import genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def test_async():
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    print("Testing async embedding...")
    emb_res = await client.aio.models.embed_content(
        model="gemini-embedding-2",
        contents="Hello World"
    )
    print("Embedding values length:", len(emb_res.embeddings[0].values))
    
    print("\nTesting async streaming generation...")
    stream = await client.aio.models.generate_content_stream(
        model="gemini-2.5-flash",
        contents="Tell me a 3-word story."
    )
    async for chunk in stream:
        print(f"Chunk: {chunk.text}", end=" | ")
    print()

if __name__ == "__main__":
    asyncio.run(test_async())
