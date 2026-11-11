import { useState } from 'react'
import './App.css'

const PROMPT_KEY = 'generate-site:prompt-history'
const MAX_HISTORY = 20
const DEFAULT_REPO = 'SlavkoPar/AIGeneratedSite'

function loadHistory() {
  try {
    const list = JSON.parse(localStorage.getItem(PROMPT_KEY) ?? '[]')
    return Array.isArray(list) ? list.filter((p) => typeof p === 'string') : []
  } catch {
    return []
  }
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
        body: JSON.stringify({ prompt, repo: repo.trim(), token: token.trim(), history: conversation, folder }),
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
      <h1>Generate Site and publish it to github</h1>
      <form onSubmit={handleSubmit}>
        <label className="field">
          GITHUB_REPO
          <input
            type="text"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            placeholder="owner/repo"
          />
        </label>
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
