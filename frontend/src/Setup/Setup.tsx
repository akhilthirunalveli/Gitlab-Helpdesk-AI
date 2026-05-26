import React, { useState } from 'react'
import { ArrowLeft02Icon } from 'hugeicons-react'
import '../Docs/Docs.css'

const CodeBlock = ({ code }: { code: string }) => {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="code-block-wrapper" style={{ position: 'relative' }}>
      <button 
        onClick={handleCopy} 
        style={{
          position: 'absolute', right: '8px', top: '8px', 
          background: copied ? 'rgba(120, 82, 238, 0.4)' : 'rgba(255, 255, 255, 0.1)', 
          border: '1px solid rgba(255, 255, 255, 0.1)', 
          color: '#fff', padding: '4px 10px', borderRadius: '6px', 
          cursor: 'pointer', fontSize: '12px', fontWeight: 500,
          transition: 'all 0.2s ease'
        }}
      >
        {copied ? 'Copied!' : 'Copy'}
      </button>
      <pre><code>{code}</code></pre>
    </div>
  )
}

export default function Setup() {
  const goBack = (e: React.MouseEvent) => {
    e.preventDefault()
    window.history.pushState({}, '', '/')
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

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
          <div className="docs-content">
            <h1>Setup Guide</h1>
          <p className="docs-intro">
            Welcome to the AI Chatbot project! Follow these instructions to get the full stack (FastAPI Backend + React Frontend) running on your local machine.
          </p>

          <section className="docs-section">
            <h2>1. Prerequisites</h2>
            <ul>
              <li><strong>Python 3.9+</strong> (for the backend)</li>
              <li><strong>Node.js 18+</strong> (for the frontend)</li>
              <li>A <a href="https://aistudio.google.com/" target="_blank" rel="noreferrer">Google Gemini API Key</a> (free tier is perfectly fine)</li>
            </ul>
          </section>

          <section className="docs-section">
            <h2>2. Backend Setup (FastAPI + RAG)</h2>
            <p>The backend handles vector search (ChromaDB) and communicates with the Gemini LLM.</p>
            
            <div className="setup-step">
              <h3>Step 2.1: Virtual Environment</h3>
              <p>Navigate to the project root and create a Python virtual environment:</p>
              <CodeBlock code={`python -m venv venv\nsource venv/bin/activate  # On Windows use: venv\\Scripts\\activate`} />
            </div>

            <div className="setup-step">
              <h3>Step 2.2: Install Dependencies</h3>
              <p>Install the required Python packages (FastAPI, Langchain, ChromaDB, etc.):</p>
              <CodeBlock code={`pip install -r backend/requirements.txt`} />
            </div>

            <div className="setup-step">
              <h3>Step 2.3: Environment Variables</h3>
              <p>Create a <code>.env</code> file in the <code>backend</code> directory and add your Gemini API key:</p>
              <CodeBlock code={`GEMINI_API_KEY="your_api_key_here"`} />
            </div>

            <div className="setup-step">
              <h3>Step 2.4: Start the Server</h3>
              <p>Run the FastAPI development server from the <code>backend</code> folder:</p>
              <CodeBlock code={`cd backend\nfastapi dev api/main.py`} />
              <p>The backend will now be running at <strong>http://localhost:8000</strong>.</p>
            </div>
          </section>

          <section className="docs-section">
            <h2>3. Frontend Setup (React + Vite)</h2>
            <p>The frontend provides the sleek, real-time streaming UI you are looking at right now.</p>
            
            <div className="setup-step">
              <h3>Step 3.1: Install Node Modules</h3>
              <p>Open a new terminal tab, navigate to the frontend folder, and install dependencies:</p>
              <CodeBlock code={`cd frontend\nnpm install`} />
            </div>

            <div className="setup-step">
              <h3>Step 3.2: Start the Dev Server</h3>
              <p>Start the Vite development server:</p>
              <CodeBlock code={`npm run dev`} />
              <p>The frontend will now be running at <strong>http://localhost:5173</strong>. It is pre-configured to proxy API requests to your local backend automatically!</p>
            </div>
          </section>

          <p style={{ fontWeight: 600, fontSize: '18px', marginTop: '32px', color: 'var(--text-primary)' }}>
            That's it! You should now have a fully functional RAG chatbot running locally. 🎉
          </p>
        </div>
        </div>
      </div>
    </div>
  )
}
