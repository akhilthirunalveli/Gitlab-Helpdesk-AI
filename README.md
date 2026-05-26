<div align="left">

# GitLab Helpdesk AI

**A smart, fast, and production-ready RAG chatbot for GitLab's Handbook.**

<img src="frontend/public/homepage.png" alt="Homepage" width="800" />

<br />

[![Live Demo](https://img.shields.io/badge/🌍_Live_Demo-gitlabhelpdesk.vercel.app-blue?style=for-the-badge)](https://gitlabhelpdesk.vercel.app/)
<br />
[![Docs](https://img.shields.io/badge/📖_Docs-Engineering_Deep_Dive-green?style=for-the-badge)](https://gitlabhelpdesk.vercel.app/docs)
<br />
[![Video](https://img.shields.io/badge/🎥_Video-Demo_Walkthrough-red?style=for-the-badge)](https://gitlabhelpdesk.vercel.app/video)
<br />
[![Setup](https://img.shields.io/badge/⚙️_Setup-Local_Guide-orange?style=for-the-badge)](https://gitlabhelpdesk.vercel.app/setup)


</div>

## Tech Stack

| | Technology | Description |
| :---: | :--- | :--- |
| ![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB) ![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat&logo=vite&logoColor=white) | **React + Vite** | High-performance frontend UI with dark mode and glassmorphism. |
| ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white) | **TypeScript** | Strongly typed frontend code for safety and scale. |
| ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white) | **FastAPI** | Python backend handling concurrent RAG logic and real-time SSE streaming. |
| ![Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?style=flat&logo=google-gemini&logoColor=white) | **Google Gemini 2.5 Flash** | Cutting-edge LLM for reasoning, embeddings, and query classification. |
| ![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6F00?style=flat&logo=databricks&logoColor=white) | **ChromaDB** | Local persistent vector database holding 900+ scraped GitLab Handbook chunks. |
| ![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) | **Python 3** | Backend runtime powering the RAG pipeline, scraper, and API layer. |


## Features

- **Real-Time Streaming** — The AI types out its answers live (just like ChatGPT) via Server-Sent Events, drastically reducing perceived latency.
- **Dynamic Context Windows** — Uses `tiktoken` to mathematically manage the LLM's memory, so the app never crashes from "Token Limit Exceeded" errors during long chats.
- **Persistent Sessions** — Your chat history is automatically saved to your browser (`localStorage`). Refresh the page and your conversation is still there.
- **Graceful Degradation** — The backend handles API rate limits (HTTP 429) with exponential backoff. If all retries fail, the user gets a friendly message instead of a raw stack trace.
- **Source Citations** — Every answer includes deduplicated source links pulled directly from the GitLab Handbook.



## Screenshots

<div align="center">
  <img src="frontend/public/chatbot-view.png" alt="Chatbot View" width="100%" />
  <br /><br />
  <img src="frontend/public/chat-example.png" alt="Chat Example" width="100%" />
</div>

---

## Local Setup

You will need two terminal windows — one for the **Backend** and one for the **Frontend**.

### 1. Start the Backend (Python)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload
```

> Backend will be running on **http://127.0.0.1:8000**

### 2. Start the Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

> Frontend will be running on **http://localhost:5173**

Open your browser, go to `http://localhost:5173`, and start chatting with **Gia**!