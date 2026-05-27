import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Wind } from 'lucide-react'

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [creds, setCreds] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async e => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      await login(creds.username, creds.password)
      nav('/')
    } catch {
      setError('Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'radial-gradient(ellipse at 30% 20%, #0d2d1e 0%, var(--bg) 60%)',
    }}>
      <div style={{ width: 380 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 10,
            background: 'linear-gradient(135deg, #10b981, #3b82f6)',
            borderRadius: 12, padding: '10px 18px', marginBottom: 16,
          }}>
            <Wind size={22} color="white" />
            <span style={{ color: 'white', fontWeight: 600, fontSize: 17, letterSpacing: '-0.02em' }}>
              Breathe ESG
            </span>
          </div>
          <div style={{ color: 'var(--muted)', fontSize: 13 }}>Emissions Intelligence Platform</div>
        </div>

        <div className="card">
          <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 4 }}>Sign in</h2>
          <p style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 24 }}>
            Demo: analyst / analyst123
          </p>

          <form onSubmit={submit}>
            <div style={{ marginBottom: 14 }}>
              <label>Username</label>
              <input
                value={creds.username}
                onChange={e => setCreds(p => ({...p, username: e.target.value}))}
                placeholder="analyst"
                autoFocus
              />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label>Password</label>
              <input
                type="password"
                value={creds.password}
                onChange={e => setCreds(p => ({...p, password: e.target.value}))}
                placeholder="••••••••"
              />
            </div>
            {error && (
              <div style={{ color: 'var(--danger)', fontSize: 12, marginBottom: 14,
                background: '#450a0a', padding: '8px 12px', borderRadius: 6 }}>
                {error}
              </div>
            )}
            <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}
              type="submit" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in →'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
