import { useEffect, useRef, useState } from 'react'

export const API_URL = import.meta.env.VITE_API_URL ?? ''
const SESSION_KEY = 'generate-site:session'
const GSI_SRC = 'https://accounts.google.com/gsi/client'

export function loadSession() {
  try {
    const session = JSON.parse(localStorage.getItem(SESSION_KEY) ?? 'null')
    return session?.token && session?.user?.email ? session : null
  } catch {
    return null
  }
}

export function saveSession(session) {
  try {
    if (session) localStorage.setItem(SESSION_KEY, JSON.stringify(session))
    else localStorage.removeItem(SESSION_KEY)
  } catch {
    // storage unavailable: the session lasts until the page is reloaded
  }
}

async function postJson(path, body) {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || `Sign-in failed (${res.status})`)
  return data
}

function loadGoogleScript() {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve()
    const script = document.createElement('script')
    script.src = GSI_SRC
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Could not load Google sign-in'))
    document.head.appendChild(script)
  })
}

export function SignIn({ onSignIn }) {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [googleReady, setGoogleReady] = useState(null) // null: loading, false: unavailable
  const googleBtn = useRef(null)

  useEffect(() => {
    let cancelled = false
    async function setup() {
      const res = await fetch(`${API_URL}/api/auth/config`)
      const { google_client_id: clientId } = await res.json()
      if (!clientId) throw new Error('not configured')
      await loadGoogleScript()
      if (cancelled) return
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async ({ credential }) => {
          setError('')
          try {
            onSignIn(await postJson('/api/auth/google', { credential }))
          } catch (err) {
            setError(err.message)
          }
        },
      })
      setGoogleReady(true)
      window.google.accounts.id.renderButton(googleBtn.current, { theme: 'outline', size: 'large', text: 'signin_with' })
    }
    setup().catch(() => !cancelled && setGoogleReady(false))
    return () => {
      cancelled = true
    }
  }, [onSignIn])

  async function submitEmail(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      onSignIn(await postJson('/api/auth/email', { email }))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="signin">
      <p className="signin-title">Sign in to generate a site</p>
      <div className="signin-options">
        <div className="signin-google">
          <div ref={googleBtn} />
          {googleReady === false && <span className="signin-note">Google sign-in is not available.</span>}
        </div>
        <span className="signin-or">or</span>
        <form className="signin-email" onSubmit={submitEmail}>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            aria-label="Email address"
            autoComplete="email"
            required
          />
          <button type="submit" disabled={busy || !email.trim()}>
            {busy ? 'Signing in…' : 'Continue with email'}
          </button>
        </form>
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  )
}
