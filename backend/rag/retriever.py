#!/usr/bin/env python3
"""
Retriever module for semantic search and prompt construction.
Generates query embeddings via Gemini embedding model
and retrieves chunks from the persistent ChromaDB database.
"""

import os
import time
import logging
import asyncio
import json
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError
from google.genai import types
import chromadb

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("gitlab_retriever")

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "data/chroma_db")

# Initialize global ChromaDB reference
_chroma_client = None
_collection = None

def get_collection():
    """
    Lazily initializes and returns the ChromaDB collection.
    """
    global _chroma_client, _collection
    if _collection is None:
        if not os.path.exists(CHROMA_DB_PATH):
            raise FileNotFoundError(f"ChromaDB not found at {CHROMA_DB_PATH}. Please run ingestion/embed_and_store.py first.")
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _collection = _chroma_client.get_collection(name="gitlab_handbook")
    return _collection

async def call_gemini_with_retry(api_func, *args, **kwargs):
    """
    Helper function to call Gemini APIs with automatic rate limit retry (max 5 retries, 65s delay for 429).
    """
    max_retries = 5
    base_delay = 2.0
    for attempt in range(max_retries + 1):
        try:
            return await api_func(*args, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = "429" in err_str or "resource_exhausted" in err_str or "resource exhausted" in err_str or "rate limit" in err_str
            
            # Check if e is an APIError and we can look at e.code
            if not is_rate_limit and hasattr(e, 'code') and e.code == 429:
                is_rate_limit = True
                
            if is_rate_limit:
                sleep_time = 65.0
                logger.warning(
                    "Rate limit (429/RESOURCE_EXHAUSTED) hit: %s. Sleeping for %.1fs before retry (Attempt %d/%d)...",
                    str(e), sleep_time, attempt + 1, max_retries
                )
            else:
                sleep_time = base_delay * (2 ** attempt) # exponential backoff for other errors
                logger.warning(
                    "API error: %s. Retrying in %.1fs (Attempt %d/%d)...",
                    str(e), sleep_time, attempt + 1, max_retries
                )
                
            if attempt < max_retries:
                await asyncio.sleep(sleep_time)
            else:
                logger.error("Gemini API failed after %d retries.", max_retries)
                raise e

async def retrieve(query: str, top_k: int = 5) -> tuple[list[dict], float]:
    """
    Generates embedding for a query, searches ChromaDB for similarity,
    and returns the top candidate chunks.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY environment variable is required")
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Generate query embedding with task prefix for asymmetric search
    formatted_query = f"task: search result | query: {query}"
    logger.info("Generating query embedding for: '%s'", formatted_query)
    response = await call_gemini_with_retry(
        client.aio.models.embed_content,
        model="gemini-embedding-2",
        contents=formatted_query
    )
    query_embedding = response.embeddings[0].values
    
    # Get collection and query ChromaDB
    collection = get_collection()
    logger.info("Querying ChromaDB for top %d matches...", top_k)
    results = await asyncio.to_thread(
        collection.query,
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    
    # Format and return the retrieved chunks
    retrieved_chunks = []
    top_distance = 1.0 # default if no results
    
    if results and "documents" in results and results["documents"]:
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0] if "distances" in results and results["distances"] else []
        
        if distances:
            top_distance = distances[0]
            
        for doc, meta in zip(documents, metadatas):
            retrieved_chunks.append({
                "text": doc,
                "url": meta.get("url", ""),
                "title": meta.get("title", "")
            })
            
    logger.info("Retrieved %d relevant chunks from ChromaDB.", len(retrieved_chunks))
    return retrieved_chunks, top_distance

def build_prompt(query: str, chunks: list[dict]) -> str:
    """
    Builds the RAG prompt with the retrieved chunks as context.
    """
    context_parts = []
    for chunk in chunks:
        part = f"[CONTEXT]\nSource: {chunk['url']}\n{chunk['text']}\n---\n[END CONTEXT]"
        context_parts.append(part)
        
    context_str = "\n\n".join(context_parts)
    
    system_instruction = (
        "You are a helpful, expert assistant for GitLab employees named Gia. "
        "If the user is simply greeting you (e.g., 'hi', 'hello', 'how are you'), "
        "respond naturally with a friendly greeting and ask how you can help them with GitLab today. "
        "For all other questions, use the provided context from GitLab's Handbook and Direction pages as your primary source of truth. "
        "If the provided context does not fully answer the user's question, you may supplement it with your general knowledge about software development, DevOps, and GitLab, "
        "but clearly prioritize and synthesize the provided context first. "
        "Always be concise, clear, and professional."
    )
    
    prompt = (
        f"{system_instruction}\n\n"
        f"{context_str}\n\n"
        f"Question: {query}\n"
        f"Answer:"
    )
    
    return prompt

if __name__ == "__main__":
    # Standard check for standalone runnable script
    # This block allows running a direct retriever search for testing
    import sys
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])
    else:
        test_query = "What is GitLab's mission?"
        
    print(f"Testing retriever with query: '{test_query}'")
    try:
        results, top_dist = asyncio.run(retrieve(test_query, top_k=5))
        print(f"\nTop vector distance: {top_dist}\n")
        for idx, res in enumerate(results):
            print(f"Match {idx+1} [Title: {res['title']}] [URL: {res['url']}]:")
            print(res['text'][:200] + "...\n")
        prompt = build_prompt(test_query, results)
        print("\nConstructed Prompt:")
        print(prompt[:500] + "...")
    except Exception as e:
        print(f"Error during retrieval: {e}")
