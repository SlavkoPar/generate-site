import { useEffect, useRef, useState } from 'react'
import './App.css'
import { DEFAULT_PROMPTS } from './defaultPrompts'

const PROMPT_KEY = 'generate-site:prompt-history'
const MAX_HISTORY = 20
const DEFAULT_REPO = 'SlavkoPar/AIGeneratedSite'

// The built-in requests are only the starting list; once the user sends one, their own
// requests are kept (newest first) and the built-ins age out like any other entry.
function loadHistory() {
  try {
    const list = JSON.parse(localStorage.getItem(PROMPT_KEY) ?? '[]')
    const saved = Array.isArray(list) ? list.filter((p) => typeof p === 'string') : []
    if (saved.length) return saved
  } catch {
    // unreadable storage: start from the built-in requests
  }
  return DEFAULT_PROMPTS
}

function App() {
  const [repo, setRepo] = useState(DEFAULT_REPO)
  const [token, setToken] = useState('') // never persisted
  const [history, setHistory] = useState(loadHistory)
  const [prompt, setPrompt] = useState(() => loadHistory()[0] ?? '')
  const [result, setResult] = useState(null)
  const [conversation, setConversation] = useState([]) // sent back so Claude can refine the last site
  const [folder, setFolder] = useState('') // GitHub folder of that site, overwritten on refinement
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const settingsRef = useRef(null)

  useEffect(() => {
    if (!settingsOpen) return undefined
    const onClick = (e) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target)) setSettingsOpen(false)
    }
    const onKey = (e) => e.key === 'Escape' && setSettingsOpen(false)
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [settingsOpen])

  async function handleSubmit(e) {
    e.preventDefault()
    const next = [prompt, ...history.filter((p) => p !== prompt)].slice(0, MAX_HISTORY)
    setHistory(next)
    try {
      localStorage.setItem(PROMPT_KEY, JSON.stringify(next))
    } catch {
      // storage unavailable (private mode etc.); continue without saving
    }
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/generate-site`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, repo: repo.trim(), token: repo.trim() !== DEFAULT_REPO ? token.trim() : '', history: conversation, folder }),
      })
      const text = await res.text()
      let data
      try {
        data = JSON.parse(text)
      } catch {
        throw new Error(
          `Server returned a non-JSON response (${res.status}). The API may be down, starting up, or timed out.`,
        )
      }
      if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`)
      setResult(data)
      setConversation(data.history ?? [])
      setFolder(data.folder ?? '')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section id="center">
      <div className="title-row">
        <h1>Generate Site and push it to github <span className="repo">{repo.trim()}</span></h1>
        <div className="settings" ref={settingsRef}>
          <button
            type="button"
            className="settings-btn"
            aria-label="Settings"
            aria-haspopup="true"
            aria-expanded={settingsOpen}
            onClick={() => setSettingsOpen((open) => !open)}
          >
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
            </svg>
          </button>
          {settingsOpen && (
            <div className="settings-menu" role="dialog" aria-label="Settings">
              <label className="field">
                GITHUB_REPO
                <input
                  type="text"
                  value={repo}
                  onChange={(e) => setRepo(e.target.value)}
                  placeholder="owner/repo"
                />
              </label>
              {repo.trim() !== DEFAULT_REPO && (
                <label className="field">
                  GITHUB_TOKEN
                  <input
                    type="password"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder="optional: defaults to the server's token"
                    autoComplete="off"
                  />
                </label>
              )}
              {repo.trim() !== DEFAULT_REPO && (
                <div className="settings-help">
                  <p>
                    Get a GitHub token that can write to your repo:{' '}
                    <a href="https://github.com/settings/personal-access-tokens" target="_blank" rel="noreferrer">
                      https://github.com/settings/personal-access-tokens
                    </a>
                  </p>
                  <p>Fine-grained token: select that repo and set Contents to Read and write.</p>
                  <p>Classic token: the repo scope is enough.</p>
                  <p>Enter that token when generating a site.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      <form onSubmit={handleSubmit}>
        {history.length > 0 && (
          <select
            value=""
            onChange={(e) => e.target.value !== '' && setPrompt(history[Number(e.target.value)])}
            aria-label="Load a previous request"
          >
            <option value="">Load a previous request…</option>
            {history.map((p, i) => (
              <option key={i} value={i}>{p.length > 80 ? `${p.slice(0, 80)}…` : p}</option>
            ))}
          </select>
        )}
        <textarea
          rows={4}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={
            conversation.length
              ? "Describe the change, e.g. 'make the header dark and add a contact form'"
              : "Describe the page, e.g. 'a landing page for a coffee shop with a menu and opening hours'"
          }
        />
        <button type="submit" disabled={loading || !prompt.trim()}>
          {loading ? 'Generating…' : 'Generate'}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      {result?.github_url && (
        <p>
          Saved to GitHub: <a href={result.github_url} target="_blank" rel="noreferrer">{result.github_url}</a>
        </p>
      )}
      {result?.usage && (
        <p className="usage">
          Claude usage: {result.usage.input_tokens.toLocaleString()} input +{' '}
          {result.usage.output_tokens.toLocaleString()} output ={' '}
          {result.usage.total_tokens.toLocaleString()} tokens, about $
          {result.usage.cost_usd.toFixed(4)} USD ({result.usage.model})
        </p>
      )}
      {result?.pages_error && <p className="error">{result.pages_error}</p>}
      {result?.github_error && <p className="error">Not saved to GitHub: {result.github_error}</p>}
      {result?.pages_url && (
        <p>
          Live on GitHub Pages (may take a minute or two to appear):{' '}
          <a href={result.pages_url} target="_blank" rel="noreferrer">{result.pages_url}</a>
        </p>
      )}
    </section>
  )
}

export default App
