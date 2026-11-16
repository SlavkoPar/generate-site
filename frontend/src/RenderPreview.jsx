import { useEffect, useState } from 'react'
import { API_URL } from './Auth'

const POLL_MS = 5000
const GIVE_UP_MS = 10 * 60 * 1000

// Preview of a site published on Render: waits for the build to finish, then shows the site.
export function RenderPreview({ url, serviceId, sessionToken }) {
  const [state, setState] = useState('building') // building | live | failed | unknown
  const [detail, setDetail] = useState('')

  useEffect(() => {
    let timer
    let stopped = false
    const started = Date.now()
    async function check() {
      try {
        const res = await fetch(`${API_URL}/api/render-status/${serviceId}`, {
          headers: { Authorization: `Bearer ${sessionToken}` },
        })
        const data = await res.json().catch(() => ({}))
        if (stopped) return
        if (!res.ok) throw new Error(data.error || `status ${res.status}`)
        if (data.state !== 'building') {
          setDetail(data.detail ?? '')
          return setState(data.state)
        }
      } catch (err) {
        if (stopped) return
        setDetail(err.message)
        return setState('unknown')
      }
      if (Date.now() - started > GIVE_UP_MS) {
        setDetail('the build is taking longer than 10 minutes')
        return setState('unknown')
      }
      timer = setTimeout(check, POLL_MS)
    }
    check()
    return () => {
      stopped = true
      clearTimeout(timer)
    }
  }, [serviceId, sessionToken])

  if (state === 'building') return <p className="usage">Preview: Render is building the site…</p>
  if (state === 'failed') return <p className="error">No preview: on Render {detail}.</p>
  if (state === 'unknown') {
    return <p className="usage">No preview: could not follow the build ({detail}). Open the link above.</p>
  }
  return (
    <div className="preview">
      <p className="usage">Preview of the generated site:</p>
      <iframe src={url} title="Preview of the generated site" sandbox="allow-scripts allow-same-origin allow-forms" />
    </div>
  )
}
