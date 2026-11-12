import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import { API_URL, SignIn, loadSession, saveSession } from './Auth'
import { DEFAULT_PROMPTS } from './defaultPrompts'
import { Help } from './Help'

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

const pageFromHash = () => (window.location.hash === '#/help' ? 'help' : 'home')

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
  const [session, setSession] = useState(loadSession)
  const [page, setPage] = useState(pageFromHash)
  const isDefaultRepo = repo.trim() === DEFAULT_REPO
  // Email sign-in carries no name, so fall back to the part before the @.
  const userName = session ? session.user.name || session.user.email.split('@')[0] : ''

  useEffect(() => {
    const onHash = () => setPage(pageFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const signIn = useCallback((next) => {
    saveSession(next)
    setSession(next)
    setError('')
  }, [])

  function signOut() {
    saveSession(null)
    setSession(null)
  }

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
      const res = await fetch(`${API_URL}/api/generate-site`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session.token}` },
        body: JSON.stringify({ prompt, repo: repo.trim(), token: isDefaultRepo ? '' : token.trim(), history: conversation, folder }),
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
      if (res.status === 401) signOut() // session expired or no longer valid: ask to sign in again
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
            className={`settings-btn${session ? ' avatar' : ''}`}
            aria-label="Profile"
            aria-haspopup="true"
            aria-expanded={settingsOpen}
            onClick={() => setSettingsOpen((open) => !open)}
          >
            {session ? (
              <span aria-hidden="true">{userName[0].toUpperCase()}</span>
            ) : (
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor"
                strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="8" r="4" />
                <path d="M4 21a8 8 0 0 1 16 0" />
              </svg>
            )}
          </button>
          {settingsOpen && (
            <div className="settings-menu" role="dialog" aria-label="Profile">
              {session ? (
                <div className="profile">
                  <span className="profile-name">{userName}</span>
                  <span className="profile-email">{session.user.email}</span>
                </div>
              ) : (
                <p className="profile-email">Not signed in. Sign in on the main page to generate a site.</p>
              )}
              <label className="field">
                GitHub repo
                <input
                  type="text"
                  value={repo}
                  onChange={(e) => setRepo(e.target.value)}
                  placeholder="owner/repo"
                />
              </label>
              <label className="field">
                GitHub token
                <input
                  type="password"
                  value={isDefaultRepo ? '' : token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder={isDefaultRepo ? "not needed: this repo uses the server's token" : 'token that can write to this repo'}
                  disabled={isDefaultRepo}
                  autoComplete="off"
                />
              </label>
              <a className="profile-link" href="#/help" onClick={() => setSettingsOpen(false)}>
                How to get a GitHub token
              </a>
              {session && (
                <button type="button" className="link-btn profile-signout" onClick={signOut}>Sign out</button>
              )}
            </div>
          )}
        </div>
      </div>
      {page === 'help' ? (
        <Help repo={repo.trim()} isDefaultRepo={isDefaultRepo} />
      ) : (
        <>
      {!session && <SignIn onSignIn={signIn} />}
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
              : "Describe the site, e.g.'a landing page for a coffee shop with a menu and opening hours'"
          }
        />
        <button type="submit" disabled={loading || !session || !prompt.trim()}>
          {loading ? 'Generating…' : session ? 'Generate' : 'Sign in to generate'}
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
          Live on GitHub Pages once the build finishes (a minute or two):{' '}
          <a href={result.pages_url} target="_blank" rel="noreferrer">{result.pages_url}</a>
        </p>
      )}
      {result?.actions_url && (
        <p>
          Build progress: <a href={result.actions_url} target="_blank" rel="noreferrer">{result.actions_url}</a>
        </p>
      )}
        </>
      )}
    </section>
  )
}

export default App
