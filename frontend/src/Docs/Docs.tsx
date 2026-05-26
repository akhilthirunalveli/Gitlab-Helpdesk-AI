import React, { useEffect, useRef } from 'react'
import { ArrowLeft02Icon } from 'hugeicons-react'
import mermaid from 'mermaid'
import './Docs.css'

export default function Docs() {
  const mermaidRef = useRef<HTMLPreElement>(null)

  const goBack = (e: React.MouseEvent) => {
    e.preventDefault()
    window.history.pushState({}, '', '/')
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  useEffect(() => {
    mermaid.initialize({ 
      startOnLoad: false, 
      theme: 'dark',
      themeVariables: {
        primaryColor: '#1a1a1c',
        primaryTextColor: '#fff',
        primaryBorderColor: '#333',
        lineColor: '#666',
        secondaryColor: '#fc6d26'
      }
    });
    
    if (mermaidRef.current) {
      mermaid.run({ nodes: [mermaidRef.current] }).catch(err => console.error("Mermaid error:", err));
    }
  }, [])

  return (
    <div className="docs-page">
      {/* ---- Navbar ---- */}
      <nav className="navbar" style={{ width: '100%', marginBottom: '24px' }}>
        <div className="navbar__logo" style={{ cursor: 'pointer' }} onClick={goBack}>
          <img src="/gitlab-logo.svg" alt="GitLab" />
          <span>GITLAB HELPDESK</span>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <a href="https://github.com/akhilthirunalveli/Gitlab-Helpdesk-AI" target="_blank" rel="noopener noreferrer" className="navbar__toggle" style={{ textDecoration: 'none' }}>
            <svg height="20" width="20" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path></svg>
            <span style={{ marginLeft: '6px' }}>GitHub</span>
          </a>
          <button
            className="navbar__toggle"
            onClick={goBack}
          >
            <ArrowLeft02Icon size={16} /> <span style={{ marginLeft: '6px' }}>Back to Home</span>
          </button>
        </div>
      </nav>

      <div className="docs-content-wrapper">
        <div className="docs-container">
          <header className="docs-header">
            <h1>Building the GitLab GenAI Helpdesk</h1>
            <p className="docs-subtitle">A quick walkthrough of my approach, decisions, and the architecture behind this project.</p>
          </header>

        <section className="docs-section">
          <h2>Hi, I'm Akhil 👋</h2>
          <p>
            When I read the project brief for this GenAI Chatbot, the core philosophy really resonated with me: <strong>transparency, collaboration, and "building in public"</strong>. GitLab is famous for its open handbook, so building a tool that helps employees actually navigate and learn from that massive wealth of knowledge felt like a really impactful problem to solve.
          </p>
          <p>
            I didn't just want to build a basic wrapper around an API. I wanted to build a product that feels <em>premium</em>, respects the user's time, and provides highly accurate, hallucination-free answers.
          </p>
        </section>

        <section className="docs-section">
          <h2>How it Works In Backend!</h2>
          <p>
            To achieve high accuracy, I implemented a <strong>Retrieval-Augmented Generation (RAG)</strong> pipeline. Instead of relying on the AI's general training data, the backend strictly searches a local vector database containing the actual GitLab Handbook and Direction pages, and uses that context to answer.
          </p>
          
          <div className="docs-mermaid-wrapper">
            <pre className="mermaid" ref={mermaidRef}>
{`graph TD
    subgraph Data Ingestion
      Scraper[GitLab Docs Scraper] -->|Extract & Clean| Chunker[Text Chunker]
      Chunker -->|Embed Documents| DocEmbed[Gemini-Embedding-2]
      DocEmbed -->|Store Vectors| Chroma[(ChromaDB)]
    end

    User([User Query]) --> Frontend[React / Vite Frontend]
    Frontend -->|POST /chat| API[FastAPI Backend]
    
    subgraph Vector Search
      API -->|Embed Query| Embed[Gemini-Embedding-2]
      Embed --> Chroma
      Chroma -->|Top K Chunks| API
    end
    
    subgraph LLM Generation
      API -->|Prompt + Context| LLM[Gemini-2.5-Flash]
      LLM -->|Streamed Response| API
    end
    
    API -->|Server-Sent Events| Frontend`}
            </pre>
          </div>
        </section>

        <section className="docs-section">
          <h2>How did I design it?</h2>
          <p>
            I built the frontend from scratch using React, drawing heavy inspiration from modern, developer-focused tools like Vercel and Linear. I specifically chose a <strong>dark-mode-first aesthetic</strong> with subtle glow effects and clean typography.
          </p>
          <ul>
            <li><strong>The "Search-First" Homepage:</strong> Instead of dropping users immediately into a confusing chat interface, the homepage acts like a search engine. You ask your initial question there, which feels much lower-friction.</li>
            <li><strong>The Chatbot Drawer:</strong> When you submit a question, a custom drawer slides in from the bottom right. I designed it this way so users can read documentation on the main screen while chatting with "Gia" (the AI assistant) on the side.</li>
            <li><strong>Source Citations:</strong> Tying back to the "build in public" requirement, transparency was key. Whenever the AI answers, it cites its sources. Users can click the little numbered circles to directly open the GitLab handbook page the AI referenced.</li>
          </ul>
        </section>

        <section className="docs-section">
          <h2>Guardrails & Edge Cases</h2>
          <p>
            One of the biggest challenges with AI is keeping it on-topic. I implemented a hybrid guardrailing system:
          </p>
          <ul>
            <li><strong>Keyword Fast-Paths:</strong> Simple greetings (like "Hi") are handled gracefully without executing a heavy vector search.</li>
            <li><strong>Relevance Checks:</strong> If the user asks something completely unrelated (e.g., "How do I bake a cake?"), the backend checks the vector distance. If the distance is too far, it falls back to a quick LLM classification check. If it's truly off-topic, the backend politely declines to answer, keeping the bot focused strictly on GitLab.</li>
          </ul>
        </section>

        <section className="docs-section">
          <h2>Engineering & UX Innovations</h2>
          <p>
            To push this project beyond a standard MVP, I focused heavily on perceived performance and backend resilience. Nobody likes staring at a blank screen while an AI thinks, so I implemented <strong>Real-time Streaming (SSE)</strong> to stream the response chunks back to the client immediately. To ensure the application never crashes during long conversations, I used `tiktoken` for <strong>Dynamic Context Window Management</strong>—this mathematically truncates older messages before we ever hit the LLM context limit. Finally, to handle the reality of free-tier API usage, I engineered the backend with exponential backoff retries and the frontend with <strong>Graceful Degradation</strong>, catching API rate limits and displaying a polished, human-friendly error message rather than exposing a raw JSON stack trace.
          </p>
          <p>
            As a final UX touch, I built <strong>Persistent Client-Side Sessions</strong> using <code>localStorage</code>. This ensures that your entire conversation history seamlessly survives any accidental page refreshes, delivering a premium, ChatGPT-like product experience without the heavy footprint of a full backend database.
          </p>
          <p>
            Finally, I focused on graceful degradation. If the API completely goes down or times out, the application doesn't just throw a raw stack trace onto the screen. Instead, it catches the error and displays a professional, human-friendly message explaining that the system is currently experiencing high demand. It's these small UX details that turn a tech demo into a production-ready product.
          </p>
          <p style={{ fontWeight: 600, fontSize: '18px', marginTop: '32px', color: 'var(--text-primary)' }}>
            Thanks for taking the time to review my project. I really enjoyed building this, and I hope the focus on product quality and robust architecture shines through!
          </p>
        </section>
      </div>
      </div>
    </div>
  )
}
