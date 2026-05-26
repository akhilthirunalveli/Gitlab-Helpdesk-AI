#!/usr/bin/env python3
"""
FastAPI application for the GitLab RAG Chatbot. Provides endpoints for chatbot conversation, health checks, and stats. Includes logging, CORS middleware, and global error handling.
"""

import sys
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import os
import tiktoken
import time
import logging
import asyncio
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError

# Import retriever from rag package
from rag import retriever

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("gitlab_api")

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Ensure API key is configured
if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
    logger.warning("GEMINI_API_KEY is not set or using placeholder. API calls will fail until set.")
    client = None
else:
    client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(
    title="GitLab Handbook RAG Chatbot API",
    description="Backend API for querying GitLab Handbook and Direction pages using RAG.",
    version="1.0.0"
)

# --------------------------------------------------------
# MIDDLEWARE
# --------------------------------------------------------

# CORS Middleware (React/Vue/etc. frontend integration)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        "Request: %s %s | Response Status: %d | Duration: %.4fs",
        request.method, request.url.path, response.status_code, duration
    )
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception occurred on path %s: %s", request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred.",
            "error": str(exc)
        }
    )

# --------------------------------------------------------
# MODEL DEFINITIONS (PYDANTIC)
# --------------------------------------------------------

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the speaker: 'user' or 'assistant'")
    content: str = Field(..., description="Content of the message")

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's query/message")
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None, 
        description="Optional list of past chat messages for conversation history"
    )

class SourceInfo(BaseModel):
    title: str
    url: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]

class HealthResponse(BaseModel):
    status: str
    message: str

class StatsResponse(BaseModel):
    total_chunks: int
    status: str

# --------------------------------------------------------
# HELPERS
# --------------------------------------------------------
def truncate_history_by_tokens(history: List[ChatMessage], max_tokens: int = 2000) -> List[ChatMessage]:
    """
    Truncates older messages from the history so the total token count is under max_tokens.
    """
    if not history:
        return []
    
    # Use cl100k_base which is standard for latest models (good approximation for Gemini)
    encoding = tiktoken.get_encoding("cl100k_base")
    
    truncated = []
    current_tokens = 0
    # Process from newest to oldest
    for msg in reversed(history):
        msg_tokens = len(encoding.encode(msg.content))
        if current_tokens + msg_tokens > max_tokens:
            logger.info("Truncating conversation history. Exceeded %d tokens.", max_tokens)
            break
        truncated.insert(0, msg)
        current_tokens += msg_tokens
        
    return truncated

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

def is_greeting_or_obvious_keyword(message: str) -> bool:
    """
    Fast path check for obvious greetings or GitLab keywords.
    """
    greetings = {"hi", "hello", "hey", "good morning", "good afternoon", "howdy", "hola", "greetings"}
    keywords = {
        "gitlab", "git lab", "handbook", "direction", "merge request", 
        "pull request", "subgroup", "epic", "devops", "sid sijbrandij", 
        "remote-first", "remote work", "gitlab values", "credit", "iteration"
    }
    words = message.lower().strip("?!.").split()
    if any(w in greetings for w in words):
        return True
    msg_lower = message.lower()
    if any(kw in msg_lower for kw in keywords):
        return True
    return False

async def is_gitlab_related(message: str) -> bool:
    """
    Guardrail to determine if the query is relevant to GitLab.
    Uses Gemini classification call (fallback slow path).
    """
    try:
        prompt = (
            "Determine if the following query is related to GitLab (the DevOps platform/company), "
            "company policies, handbook, direction, work culture, organizational structure, "
            "or technical questions about using GitLab.\n"
            "Respond with only 'YES' or 'NO'. Do not explain.\n\n"
            f"Query: \"{message}\"\n"
            "Response:"
        )
        response = await call_gemini_with_retry(
            client.aio.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
            config={"temperature": 0.0, "max_output_tokens": 10}
        )
        result_text = response.text.strip().upper()
        return "YES" in result_text
    except Exception as e:
        logger.error("Error during relevance check classification: %s", str(e))
        # Fallback to True so we do not block legitimate requests if classification fails
        return True

# --------------------------------------------------------
# ENDPOINTS
# --------------------------------------------------------

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    POST /chat
    Core chatbot RAG endpoint. Validates message topic, retrieves context chunks,
    incorporates chat history (last 3 exchanges), and streams the final answer using Server-Sent Events (SSE).
    """
    message = request.message.strip()
    if not message:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Message cannot be empty."}
        )

    async def event_generator():
        # Check fast path
        is_related = is_greeting_or_obvious_keyword(message)
        top_dist = 1.0
        chunks = []
        
        try:
            chunks, top_dist = await retriever.retrieve(message, top_k=15)
        except FileNotFoundError as e:
            logger.error("Retriever database not ready: %s", str(e))
            yield f"data: {json.dumps({'type': 'error', 'error': 'Retriever database not ready. Please verify ingestion is complete.'})}\n\n"
            yield "data: [DONE]\n\n"
            return
        except Exception as e:
            logger.error("Error during retrieval: %s", str(e))
            yield f"data: {json.dumps({'type': 'error', 'error': 'Failed to retrieve documents for prompt context.'})}\n\n"
            yield "data: [DONE]\n\n"
            return
            
        # If not matched by fast path, check top chunk distance (hybrid guardrail)
        if not is_related:
            if chunks and top_dist < 0.75:
                is_related = True
            else:
                # Fallback to LLM classification
                try:
                    is_related = await is_gitlab_related(message)
                except Exception as e:
                    logger.error("Error in LLM relevance check: %s", str(e))
                    is_related = True
                    
        if not is_related:
            yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
            blocked_msg = (
                "I'm only able to answer questions about GitLab's "
                "Handbook and Direction. Please ask something related "
                "to GitLab."
            )
            yield f"data: {json.dumps({'type': 'content', 'content': blocked_msg})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Deduplicate sources by URL
        seen_urls = set()
        deduped_sources = []
        for chunk in chunks:
            url = chunk["url"]
            if url not in seen_urls:
                seen_urls.add(url)
                deduped_sources.append({
                    "title": chunk["title"],
                    "url": url
                })

        # Yield sources first
        yield f"data: {json.dumps({'type': 'sources', 'sources': deduped_sources})}\n\n"

        # Build prompt context and call Gemini
        rag_prompt = retriever.build_prompt(message, chunks)
        contents = []

        if request.conversation_history:
            history_to_include = truncate_history_by_tokens(request.conversation_history, max_tokens=1500)
            for chat_msg in history_to_include:
                role = "user" if chat_msg.role == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": chat_msg.content}]
                })

        contents.append({
            "role": "user",
            "parts": [{"text": rag_prompt}]
        })

        try:
            stream = await call_gemini_with_retry(
                client.aio.models.generate_content_stream,
                model="gemini-2.5-flash",
                contents=contents,
                config={
                    "temperature": 0.2,
                    "max_output_tokens": 1024
                }
            )
            async for chunk in stream:
                if chunk.text:
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk.text})}\n\n"
        except Exception as e:
            logger.error("Error during streaming generation: %s", str(e))
            error_msg = {"type": "error", "error": "I'm currently experiencing high demand and having trouble connecting to my knowledge base. Please try asking your question again in a moment."}
            yield f"data: {json.dumps(error_msg)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/health", response_model=HealthResponse)
async def health_endpoint():
    """
    GET /health
    Simple endpoint checking if the API service is up and running.
    """
    return HealthResponse(
        status="ok",
        message="GitLab Chatbot API is running"
    )

@app.get("/stats", response_model=StatsResponse)
async def stats_endpoint():
    """
    GET /stats
    Returns count of total ingested chunks and status of retrieval readiness.
    """
    try:
        collection = retriever.get_collection()
        count = await asyncio.to_thread(collection.count)
        return StatsResponse(
            total_chunks=count,
            status="ready" if count > 0 else "empty"
        )
    except Exception as e:
        logger.warning("Retrieval database is not ready or accessible: %s", str(e))
        return StatsResponse(
            total_chunks=0,
            status="not_ready"
        )

import os
from fastapi.staticfiles import StaticFiles

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    logger.warning("Frontend dist directory not found at %s. UI will not be served.", frontend_dir)

if __name__ == "__main__":
    import uvicorn
    # Allow running the API directly using: python api/main.py
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
