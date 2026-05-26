import { useState, useRef, useEffect, useCallback, type FormEvent } from 'react'
import { ArrowUp02Icon as SendIcon, Message01Icon as ChatIcon, Cancel01Icon as CloseIcon, Link01Icon as LinkIcon, Search02Icon as SearchIcon, ArrowUpRight01Icon, ArrowExpand01Icon, ArrowShrink01Icon, Delete02Icon } from 'hugeicons-react'
import './App.css'

/* ────────────────────────────────────────────
   Types
   ──────────────────────────────────────────── */
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: { title: string; url: string }[]
}

type Mode = 'landing' | 'chat'



/* ────────────────────────────────────────────
   Helpers
   ──────────────────────────────────────────── */
const uid = () => Math.random().toString(36).slice(2, 10)

const API_BASE = import.meta.env.DEV ? 'http://localhost:8000' : 'https://gitlab-helpdesk-backend.onrender.com'

/** Renders very basic markdown: **bold**, `code`, newlines, lists */
function renderMarkdown(text: string) {
  const lines = text.split('\n')
  const elements: React.JSX.Element[] = []
  let listItems: string[] = []
  let listType: 'ul' | 'ol' | null = null

  const flushList = () => {
    if (listItems.length > 0 && listType) {
      const Tag = listType
      elements.push(
        <Tag key={elements.length}>
          {listItems.map((li, i) => <li key={i} dangerouslySetInnerHTML={{ __html: inlineFormat(li) }} />)}
        </Tag>
      )
      listItems = []
      listType = null
    }
  }

  const inlineFormat = (s: string) =>
    s.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
     .replace(/`(.*?)`/g, '<code>$1</code>')

  for (const line of lines) {
    const ulMatch = line.match(/^[-*]\s+(.+)/)
    const olMatch = line.match(/^\d+\.\s+(.+)/)

    if (ulMatch) {
      if (listType !== 'ul') flushList()
      listType = 'ul'
      listItems.push(ulMatch[1])
    } else if (olMatch) {
      if (listType !== 'ol') flushList()
      listType = 'ol'
      listItems.push(olMatch[1])
    } else {
      flushList()
      const trimmed = line.trim()
      if (trimmed) {
        elements.push(<p key={elements.length} dangerouslySetInnerHTML={{ __html: inlineFormat(trimmed) }} />)
      }
    }
  }
  flushList()
  return elements
}

/* ────────────────────────────────────────────
   Components
   ──────────────────────────────────────────── */

const SUGGESTIONS = [
  "How do I reset 2FA?",
  "Setup CI/CD pipeline",
  "Fix merge conflict",
]

const MessageSources = ({ sources }: { sources: { title: string; url: string }[] }) => {
  const [isOpen, setIsOpen] = useState(false)
  const popoverRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  if (!sources || sources.length === 0) return null

  return (
    <div className="sources-container" ref={popoverRef}>
      <div 
        className="sources-circles" 
        onClick={() => setIsOpen(!isOpen)}
        title={`${sources.length} sources`}
      >
        <span className="sources-label">Sources</span>
        {sources.slice(0, 3).map((s, i) => (
          <div key={i} className="source-circle" style={{ zIndex: 3 - i }}>
            {i + 1}
          </div>
        ))}
        {sources.length > 3 && (
          <div className="source-circle source-circle--more" style={{ zIndex: 0 }}>
            +{sources.length - 3}
          </div>
        )}
      </div>
      
      {isOpen && (
        <div className="sources-popover">
          <div className="sources-popover__list">
            {sources.map((s, i) => (
              <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" className="source-item">
                <span className="source-item__title">{s.title || 'Source'}</span>
                <LinkIcon size={14} />
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/* ────────────────────────────────────────────
   App Component
   ──────────────────────────────────────────── */
function App() {
  const [mode, setMode] = useState<Mode>('landing')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerExpanded, setDrawerExpanded] = useState(false)
  
  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = localStorage.getItem('gitlab_helpdesk_messages')
    if (saved) {
      try {
        return JSON.parse(saved)
      } catch (e) {
        // ignore
      }
    }
    return [
      {
        id: 'greeting',
        role: 'assistant',
        content: "Hi! I'm Gia. How can I help you with GitLab today?"
      }
    ]
  })
  
  const [inputValue, setInputValue] = useState('')
  const [drawerInput, setDrawerInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const drawerMessagesEndRef = useRef<HTMLDivElement>(null)
  const chatInputRef = useRef<HTMLInputElement>(null)
  const drawerInputRef = useRef<HTMLInputElement>(null)

  /* Save to localStorage whenever messages change */
  useEffect(() => {
    localStorage.setItem('gitlab_helpdesk_messages', JSON.stringify(messages))
  }, [messages])

  /* Auto-scroll to bottom */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    drawerMessagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, drawerOpen])

  /* ---- Send message via SSE ---- */
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isStreaming) return

    const userMsg: Message = { id: uid(), role: 'user', content: text.trim() }
    const botId = uid()

    setMessages(prev => [...prev, userMsg])
    setIsStreaming(true)

    // Build conversation history for backend
    const history = messages.map(m => ({ role: m.role, content: m.content }))

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text.trim(),
          conversation_history: history,
        }),
      })

      if (!res.ok || !res.body) {
        throw new Error(`Server error: ${res.status}`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let botContent = ''
      let sources: { title: string; url: string }[] = []
      let botMsgCreated = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6).trim()
          if (payload === '[DONE]') continue

          try {
            const data = JSON.parse(payload)

            if (data.type === 'sources') {
              sources = data.sources || []
            } else if (data.type === 'content') {
              botContent += data.content

              if (!botMsgCreated) {
                botMsgCreated = true
                setMessages(prev => [...prev, { id: botId, role: 'assistant', content: botContent, sources }])
              } else {
                setMessages(prev =>
                  prev.map(m => m.id === botId ? { ...m, content: botContent, sources } : m)
                )
              }
            } else if (data.type === 'error') {
              botContent = data.error || 'Something went wrong.'
              if (!botMsgCreated) {
                botMsgCreated = true
                setMessages(prev => [...prev, { id: botId, role: 'assistant', content: botContent }])
              } else {
                setMessages(prev =>
                  prev.map(m => m.id === botId ? { ...m, content: botContent } : m)
                )
              }
            }
          } catch {
            // skip unparseable lines
          }
        }
      }

      // If we never created a bot message (empty stream), add a fallback
      if (!botMsgCreated) {
        setMessages(prev => [
          ...prev,
          { id: botId, role: 'assistant', content: 'No response received. Please try again.' },
        ])
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: botId,
          role: 'assistant',
          content: `Connection error: ${err instanceof Error ? err.message : 'Unknown error'}. Is the backend running?`,
        },
      ])
    } finally {
      setIsStreaming(false)
      // Refocus input
      setTimeout(() => {
        chatInputRef.current?.focus()
        drawerInputRef.current?.focus()
      }, 100)
    }
  }, [isStreaming, messages])

  /* ---- Handlers ---- */
  const handleLandingSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim()) return
    setMode('chat')
    sendMessage(inputValue)
    setInputValue('')
  }

  const handleChatSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim()) return
    sendMessage(inputValue)
    setInputValue('')
  }

  const handleDrawerSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!drawerInput.trim()) return
    if (mode === 'landing') setMode('chat')
    sendMessage(drawerInput)
    setDrawerInput('')
  }

  const toggleDrawer = () => setDrawerOpen(prev => !prev)

  /* ────────────────────────────────────────────
     Render
     ──────────────────────────────────────────── */
  return (
    <>
      {/* ---- Navbar ---- */}
      <nav className="navbar">
        <div className="navbar__logo" style={{ cursor: 'pointer' }} onClick={() => { setMode('landing'); setDrawerOpen(false); }}>
          <img src="/gitlab-logo.svg" alt="GitLab" />
          <span>GITLAB HELPDESK</span>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          {messages.length > 1 && (
            <button
              className="navbar__toggle"
              onClick={() => setMessages([{ id: 'greeting', role: 'assistant', content: "Hi! I'm Gia. How can I help you with GitLab today?" }])}
              style={{ background: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
            >
              <Delete02Icon size={16} /> <span style={{ marginLeft: '6px' }}>Clear Chat</span>
            </button>
          )}
          <button
            className={`navbar__toggle ${drawerOpen ? 'navbar__toggle--active' : ''}`}
            onClick={toggleDrawer}
            id="drawer-toggle"
          >
            {drawerOpen ? (
              <><CloseIcon size={16} /> <span style={{ marginLeft: '6px' }}>Close</span></>
            ) : (
              <><ChatIcon size={16} /> <span style={{ marginLeft: '6px' }}>Chatbot View</span></>
            )}
          </button>
        </div>
      </nav>

      {/* ---- Main Content ---- */}
      <main className="main">
        {/* Landing Hero */}
        {mode === 'landing' && !drawerOpen && (
          <section className="hero">
            <img className="hero__logo" src="/gitlab-logo.svg" alt="GitLab logo" />
            <h1 className="hero__heading">GitLab Helpdesk</h1>
            <p className="hero__tagline">
              Ask anything about your repos, pipelines, issues, and more.
            </p>
            <form className="ask-bar" onSubmit={handleLandingSubmit}>
              <div className="ask-bar__wrapper">
                <img className="ask-bar__logo" src="/gitlab-logo.svg" alt="" />
                <input
                  className="ask-bar__input"
                  type="text"
                  placeholder="Ask a question..."
                  value={inputValue}
                  onChange={e => setInputValue(e.target.value)}
                  autoFocus
                  id="landing-input"
                />
                <button className="ask-bar__submit" type="submit" disabled={!inputValue.trim() || isStreaming}>
                  <SearchIcon/>
                </button>
              </div>
            </form>

            <div className="landing-suggestions">
              {SUGGESTIONS.map((s, i) => (
                <button 
                  key={i} 
                  className="suggestion-pill"
                  onClick={() => {
                    setInputValue(s)
                    setMode('chat')
                    sendMessage(s)
                    setInputValue('')
                  }}
                >
                  {s}
                </button>
              ))}
            </div>

            {/* ---- Homepage Bottom Left Links ---- */}
            <div className="landing-links">
              <a href="https://github.com/akhilthirunalveli/Gitlab-Helpdesk-AI" target="_blank" rel="noopener noreferrer" className="landing-link">
                GitHub
                <ArrowUpRight01Icon size={14} />
              </a>
              <a href="/setup" className="landing-link" onClick={(e) => {
                e.preventDefault();
                window.history.pushState({}, '', '/setup');
                window.dispatchEvent(new PopStateEvent('popstate'));
              }}>
                Setup
                <ArrowUpRight01Icon size={14} />
              </a>
              <a href="/docs" className="landing-link" onClick={(e) => {
                e.preventDefault();
                window.history.pushState({}, '', '/docs');
                window.dispatchEvent(new PopStateEvent('popstate'));
              }}>
                Docs
                <ArrowUpRight01Icon size={14} />
              </a>
              <a href="#" className="landing-link">
                Video
                <ArrowUpRight01Icon size={14} />
              </a>
            </div>
          </section>
        )}

        {/* Chat Mode */}
        {mode === 'chat' && !drawerOpen && (
          <section className="chat">
            <div className="chat__messages">
              {messages.map(msg => (
                <div key={msg.id} className={`msg msg--${msg.role === 'user' ? 'user' : 'bot'}`}>
                  {msg.role === 'assistant' ? renderMarkdown(msg.content) : msg.content}
                  {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                    <MessageSources sources={msg.sources} />
                  )}
                </div>
              ))}
              {isStreaming && messages[messages.length - 1]?.role === 'user' && (
                <div className="typing">
                  <span className="typing__dot" />
                  <span className="typing__dot" />
                  <span className="typing__dot" />
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <form className="chat__input-bar" onSubmit={handleChatSubmit}>
              <input
                ref={chatInputRef}
                className="chat__input"
                type="text"
                placeholder="Type a message..."
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                id="chat-input"
              />
              <button className="chat__send" type="submit" disabled={!inputValue.trim() || isStreaming}>
                <SendIcon />
              </button>
            </form>
          </section>
        )}
      </main>

      {/* ---- Drawer Overlay ---- */}
      <div
        className={`drawer-overlay ${drawerOpen ? 'drawer-overlay--visible' : ''}`}
        onClick={toggleDrawer}
      />

      {/* ---- Bottom Drawer ---- */}
      <aside className={`drawer ${drawerOpen ? 'drawer--open' : ''} ${drawerExpanded ? 'drawer--expanded' : ''}`}>
        <div className="drawer__handle">
          <div className="drawer__handle-bar" />
        </div>
        <div className="drawer__header">
          <div className="drawer__identity">
            <div className="drawer__avatar-wrapper">
              <img className="drawer__avatar" src="/GenAI-Girl.jpg" alt="Gia" />
            </div>
            <div className="drawer__identity-text">
              <span className="drawer__title">Gia</span>
              <span className="drawer__subtitle">AI Assistant</span>
            </div>
          </div>
          <div className="drawer__actions">
            {messages.length > 1 && (
              <button 
                className="drawer__action-btn" 
                onClick={() => setMessages([{ id: 'greeting', role: 'assistant', content: "Hi! I'm Gia. How can I help you with GitLab today?" }])} 
                title="Clear Chat"
              >
                <Delete02Icon size={16} />
              </button>
            )}
            <button className="drawer__action-btn" onClick={() => setDrawerExpanded(prev => !prev)} title={drawerExpanded ? "Shrink" : "Expand"}>
              {drawerExpanded ? <ArrowShrink01Icon size={15} /> : <ArrowExpand01Icon size={15} />}
            </button>
            <button className="drawer__action-btn" onClick={toggleDrawer}>
              <CloseIcon size={15} />
            </button>
          </div>
        </div>

        <div className="drawer__messages">
          {messages.length === 0 && (
            <div className="drawer__empty">
              <img className="drawer__empty-logo" src="/gitlab-logo.svg" alt="" />
              <p className="drawer__empty-text">Ask anything about GitLab</p>
              <span className="drawer__empty-hint">Repos · Pipelines · Issues · CI/CD</span>
            </div>
          )}
          {messages.map(msg => (
            <div key={msg.id} className={`msg msg--${msg.role === 'user' ? 'user' : 'bot'}`}>
              {msg.role === 'assistant' ? renderMarkdown(msg.content) : msg.content}
              {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                <MessageSources sources={msg.sources} />
              )}
            </div>
          ))}
          {isStreaming && messages[messages.length - 1]?.role === 'user' && (
            <div className="typing">
              <span className="typing__dot" />
              <span className="typing__dot" />
              <span className="typing__dot" />
            </div>
          )}
          <div ref={drawerMessagesEndRef} />
        </div>

        <form className="drawer__input-bar" onSubmit={handleDrawerSubmit}>
          <input
            ref={drawerInputRef}
            className="drawer__input"
            type="text"
            placeholder="Ask a question..."
            value={drawerInput}
            onChange={e => setDrawerInput(e.target.value)}
            id="drawer-input"
          />
          <button className="drawer__send" type="submit" disabled={!drawerInput.trim() || isStreaming}>
            <SendIcon />
          </button>
        </form>
      </aside>
    </>
  )
}

export default App
