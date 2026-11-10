import { useState } from 'react'
import './App.css'

function CodePane({ title, code }) {
  return (
    <div className="code-pane">
      <div className="code-pane-header">
        <strong>{title}</strong>
        <button onClick={() => navigator.clipboard.writeText(code)}>Copy</button>
      </div>
      <pre>
        <code>{code}</code>
      </pre>
    </div>
  )
}

function App() {
  const [prompt, setPrompt] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section id="center">
      <h1>Generate Code</h1>
      <form onSubmit={handleSubmit}>
        <textarea
          rows={4}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe what the code should do, e.g. 'read a CSV file and print the sum of the price column'"
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
      {result?.github_error && <p className="error">Not saved to GitHub: {result.github_error}</p>}
      {result && (
        <div className="code-panes">
          <CodePane title="Python" code={result.python} />
          <CodePane title="JavaScript" code={result.javascript} />
        </div>
      )}
    </section>
  )
}

export default App
