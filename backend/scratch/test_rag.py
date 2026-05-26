#!/usr/bin/env python3
"""
Test script for verifying RAG chatbot workflow end-to-end.
"""

import os
import json
import sys
import requests
from dotenv import load_dotenv

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set dummy environment variable values if not already present
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def run_tests():
    print("=== STARTING END-TO-END RAG TEST ===")
    
    # 1. Verify requirements
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        print("[WARNING] GEMINI_API_KEY is not set or is using placeholder. AI API calls will fail.")
        
    # 2. Check if scraped data exists
    scraped_path = "data/scraped_pages.json"
    if not os.path.exists(scraped_path):
        print(f"[ERROR] Scraped data not found at {scraped_path}. Please run scrape_gitlab.py first.")
        return False
        
    print(f"[OK] Found scraped pages at {scraped_path}.")
    
    # Load and print summary of scraped data
    with open(scraped_path, "r", encoding="utf-8") as f:
        scraped_data = json.load(f)
    print(f"Total scraped pages: {len(scraped_data)}")
    if len(scraped_data) > 0:
        print(f"Sample page: {scraped_data[0]['title']} ({scraped_data[0]['url']})")
        
    # 3. Check ChromaDB directory
    chroma_path = "data/chroma_db"
    if not os.path.exists(chroma_path):
        print(f"[WARNING] ChromaDB folder not found at {chroma_path}. Run embed_and_store.py.")
    else:
        print(f"[OK] Found ChromaDB folder at {chroma_path}.")
        
    # 4. Perform direct retrieval test (if key is present)
    if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
        try:
            print("\n--- Running direct retriever test ---")
            from rag import retriever
            test_query = "What is GitLab's mission?"
            chunks = retriever.retrieve(test_query, top_k=2)
            print(f"Successfully retrieved {len(chunks)} chunks.")
            for i, chunk in enumerate(chunks):
                print(f"Chunk {i+1} title: {chunk['title']} | Source: {chunk['url']}")
                print(f"Content snippet: {chunk['text'][:150]}...")
        except Exception as e:
            print(f"[ERROR] Direct retrieval test failed: {e}")
            
    print("\n=== VERIFYING API SERVER (Localhost:8000) ===")
    api_url = "http://localhost:8000"
    
    # Check if API server is running
    try:
        health_resp = requests.get(f"{api_url}/health", timeout=3)
        if health_resp.status_code == 200:
            print("[OK] Health endpoint returned 200.")
            print("Response:", health_resp.json())
        else:
            print(f"[ERROR] Health endpoint returned status: {health_resp.status_code}")
    except requests.exceptions.ConnectionError:
        print("[INFO] API server is not running on localhost:8000. Skipping API endpoints test.")
        return True
        
    # Check stats endpoint
    try:
        stats_resp = requests.get(f"{api_url}/stats", timeout=3)
        print("[OK] Stats endpoint response:", stats_resp.json())
    except Exception as e:
        print(f"[ERROR] Failed to query /stats: {e}")
        
    # Check chat endpoint (on-topic)
    try:
        payload = {
            "message": "What is GitLab's direction or mission?",
            "conversation_history": []
        }
        chat_resp = requests.post(f"{api_url}/chat", json=payload, timeout=10)
        if chat_resp.status_code == 200:
            print("[OK] On-topic chat query succeeded.")
            data = chat_resp.json()
            print("Answer preview:", data.get("answer", "")[:300] + "...")
            print("Sources:", data.get("sources", []))
        else:
            print(f"[ERROR] Chat query failed with status: {chat_resp.status_code}")
            print(chat_resp.text)
    except Exception as e:
        print(f"[ERROR] Chat endpoint error: {e}")
        
    # Check chat endpoint (off-topic guardrail)
    try:
        payload = {
            "message": "How do I make chocolate chip cookies?",
            "conversation_history": []
        }
        chat_resp = requests.post(f"{api_url}/chat", json=payload, timeout=10)
        if chat_resp.status_code == 200:
            data = chat_resp.json()
            answer = data.get("answer", "")
            print("[OK] Off-topic query processed.")
            print("Answer:", answer)
            if "I'm only able to answer questions about GitLab's Handbook" in answer:
                print("[OK] Guardrail trigger verified.")
            else:
                print("[WARNING] Guardrail did not trigger as expected.")
        else:
            print(f"[ERROR] Off-topic query failed with status: {chat_resp.status_code}")
    except Exception as e:
        print(f"[ERROR] Guardrail test error: {e}")
        
    return True

if __name__ == "__main__":
    run_tests()
