#!/usr/bin/env python3
"""
Ingestion script for embedding scraped pages and storing them in ChromaDB.
Uses LangChain's RecursiveCharacterTextSplitter and Gemini's embedding model.
"""

import os
import json
import time
import logging
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError
from google.genai import types
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("gitlab_ingestion")

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "data/chroma_db")
SCRAPED_DATA_PATH = os.getenv("SCRAPED_DATA_PATH", "data/scraped_pages.json")

# Ensure API key is configured
if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
    logger.error("GEMINI_API_KEY is not set in the environment or .env file.")
    # We will raise an error or exit so the script fails gracefully
    raise ValueError("GEMINI_API_KEY environment variable is required")

client = genai.Client(api_key=GEMINI_API_KEY)

def call_gemini_with_retry(api_func, *args, **kwargs):
    """
    Executes a Gemini API call with rate limit retries (max 5 retries, 65s delay for 429).
    """
    max_retries = 5
    base_delay = 2.0
    for attempt in range(max_retries + 1):
        try:
            return api_func(*args, **kwargs)
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
                time.sleep(sleep_time)
            else:
                logger.error("Gemini API failed after %d retries.", max_retries)
                raise e

def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """
    Generates embeddings for a batch of document chunks using Gemini's gemini-embedding-2 model.
    """
    contents = [types.Content(parts=[types.Part.from_text(text=t)]) for t in texts]
    response = call_gemini_with_retry(
        client.models.embed_content,
        model="gemini-embedding-2",
        contents=contents
    )
    return [e.values for e in response.embeddings]

def embed_and_store() -> None:
    """
    Loads data/scraped_pages.json, chunks the documents, generates embeddings,
    and stores them in ChromaDB.
    """
    if not os.path.exists(SCRAPED_DATA_PATH):
        logger.error("Scraped data file not found at %s. Please run the scraper first.", SCRAPED_DATA_PATH)
        return
        
    with open(SCRAPED_DATA_PATH, "r", encoding="utf-8") as f:
        pages = json.load(f)
        
    logger.info("Loaded %d pages from %s", len(pages), SCRAPED_DATA_PATH)
    
    # Initialize ChromaDB client
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    # Delete existing collection to rebuild
    try:
        chroma_client.delete_collection(name="gitlab_handbook")
        logger.info("Deleted existing 'gitlab_handbook' collection for rebuild.")
    except Exception:
        pass
        
    # Create or get collection
    collection = chroma_client.get_or_create_collection(name="gitlab_handbook")
        
    # Set up Semantic Markdown Splitter
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    # Fallback character splitter in case a single markdown section is massive
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )
    
    chunks = []
    for page in pages:
        url = page.get("url", "")
        title = page.get("title", "")
        content = page.get("content", "")
        
        if not content.strip():
            continue
            
        # 1. Split by markdown headers
        md_docs = markdown_splitter.split_text(content)
        
        # 2. Split resulting sections by characters if they are too long
        final_docs = char_splitter.split_documents(md_docs)
        
        for i, doc in enumerate(final_docs):
            # doc.page_content holds the text
            # doc.metadata holds the headers e.g. {"Header 1": "Introduction", ...}
            
            # Reconstruct context string by including headers
            header_context = " > ".join([v for k, v in doc.metadata.items() if k.startswith("Header")])
            full_text = f"[{header_context}]\n{doc.page_content}" if header_context else doc.page_content
            
            chunks.append({
                "id": f"{url}_chunk_{i}",
                "text": full_text,
                "metadata": {
                    "url": url,
                    "title": title
                }
            })
            
    logger.info("Generated %d total chunks from %d pages.", len(chunks), len(pages))
    logger.info("Starting embedding generation and storage in ChromaDB...")
    
    # Process chunks and add to ChromaDB in batches to be fast and respect rate limits
    chunk_count = 0
    batch_size = 100
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        batch_texts = [chunk["text"] for chunk in batch]
        batch_ids = [chunk["id"] for chunk in batch]
        batch_metadatas = [chunk["metadata"] for chunk in batch]
        
        # Format the text with the title prefix for asymmetric search
        formatted_texts = []
        for chunk in batch:
            title = chunk["metadata"].get("title") or "none"
            formatted_texts.append(f"title: {title} | text: {chunk['text']}")
            
        try:
            # Generate embeddings for the formatted batch
            vectors = generate_embeddings_batch(formatted_texts)
            
            # Store original texts and metadata along with the embeddings in ChromaDB
            collection.add(
                ids=batch_ids,
                embeddings=vectors,
                documents=batch_texts,
                metadatas=batch_metadatas
            )
            
            chunk_count += len(batch)
            logger.info("Processed and stored %d/%d chunks...", chunk_count, len(chunks))
            
            # Avoid sudden bursts of requests
            if i + batch_size < len(chunks):
                time.sleep(1.0)
            
        except Exception as e:
            logger.error("Failed to process batch starting at index %d: %s", i, str(e))
            
    logger.info("Ingestion completed. Successfully stored %d chunks in ChromaDB.", chunk_count)

if __name__ == "__main__":
    embed_and_store()
