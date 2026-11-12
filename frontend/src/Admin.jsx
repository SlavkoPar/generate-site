import { useEffect, useState } from 'react'
import { API_URL } from './Auth'

const when = (iso) => new Date(iso).toLocaleString()

// Users tab (#/users), administrator only: every registered user and their generations.
export function Admin({ sessionToken }) {
  const [users, setUsers] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    fetch(`${API_URL}/api/admin/users`, { headers: { Authorization: `Bearer ${sessionToken}` } })
      .then(async (res) => {
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(data.error || `Could not load users (${res.status})`)
        if (!cancelled) setUsers(data.users)
      })
      .catch((err) => !cancelled && setError(err.message))
    return () => {
      cancelled = true
    }
  }, [sessionToken])

  if (error) return <p className="error">{error}</p>
  if (!users) return <p className="usage">Loading users…</p>

  const totalCost = users.reduce((sum, u) => sum + u.total_cost_usd, 0)
  const totalGenerations = users.reduce((sum, u) => sum + u.generation_count, 0)

  return (
    <div className="admin">
      <p className="admin-summary">
        {users.length} registered user{users.length === 1 ? '' : 's'}, {totalGenerations} generation
        {totalGenerations === 1 ? '' : 's'}, ${totalCost.toFixed(4)} Claude cost in total
      </p>
      {users.map((u) => (
        <details key={u.email}>
          <summary>
            <strong>{u.name ? `${u.name} (${u.email})` : u.email}</strong>
            <span className="admin-meta">
              {u.provider} sign-in · {u.generation_count} generation{u.generation_count === 1 ? '' : 's'} · $
              {u.total_cost_usd.toFixed(4)} · last sign-in {when(u.last_login_at)}
            </span>
          </summary>
          <p className="admin-empty">
            Registered {when(u.created_at)} · repo: {u.github_repo || 'default'} · token saved:{' '}
            {u.has_github_token ? 'yes' : 'no'}
          </p>
          {u.generations.length === 0 ? (
            <p className="admin-empty">No generations yet.</p>
          ) : (
            <div className="admin-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Request</th>
                    <th>Repo</th>
                    <th>Tokens</th>
                    <th>Cost</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {u.generations.map((g, i) => (
                    <tr key={i}>
                      <td>{when(g.created_at)}</td>
                      <td className="prompt">{g.prompt}</td>
                      <td>{g.repo}</td>
                      <td className="num">{(g.input_tokens + g.output_tokens).toLocaleString()}</td>
                      <td className="num">${g.cost_usd.toFixed(4)}</td>
                      <td>
                        {g.error ? (
                          <span className="error">{g.error}</span>
                        ) : (
                          <>
                            {g.github_url && <a href={g.github_url} target="_blank" rel="noreferrer">source</a>}
                            {g.github_url && g.pages_url && ' · '}
                            {g.pages_url && <a href={g.pages_url} target="_blank" rel="noreferrer">site</a>}
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {u.generation_count > u.generations.length && (
                <p className="admin-meta">Showing the latest {u.generations.length} of {u.generation_count}.</p>
              )}
            </div>
          )}
        </details>
      ))}
    </div>
  )
}
