import os
import asyncio
from dotenv import load_dotenv
from google import genai
import chromadb

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHROMA_DB_PATH = "data/chroma_db"

async def test():
    client = genai.Client(api_key=GEMINI_API_KEY)
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = chroma_client.get_collection(name="gitlab_handbook")
    
    queries = [
        "What are the core values of GitLab?",
        "How does iteration work?",
        "What is the mission?",
        "recipe for baking a chocolate cake",
        "who is the prime minister of India",
        "how to build a react app",
        "hello",
        "hey there"
    ]
    
    print("Testing query distances:")
    for q in queries:
        formatted_query = f"task: search result | query: {q}"
        response = await client.aio.models.embed_content(
            model="gemini-embedding-2",
            contents=formatted_query
        )
        query_embedding = response.embeddings[0].values
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=1
        )
        
        distance = results["distances"][0][0] if results["distances"] else None
        doc_preview = results["documents"][0][0][:60].replace('\n', ' ') if results["documents"] else ""
        print(f"Query: '{q}'\n  Distance: {distance}\n  Closest Match: {doc_preview}...\n")

if __name__ == "__main__":
    asyncio.run(test())
