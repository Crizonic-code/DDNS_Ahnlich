import React, { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = '/api'

function App() {
  const [view, setView] = useState('landing') // landing, login, register, dashboard
  const [user, setUser] = useState(null)
  const [hostnames, setHostnames] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Check auth on mount
  useEffect(() => {
    const token = localStorage.getItem('ddns_token')
    if (token) {
      axios.get(`${API_BASE}/me`, { headers: { 'X-JWT-Token': token } })
        .then(res => {
          setUser(res.data)
          setView('dashboard')
          loadHostnames(token)
        })
        .catch(() => {
          localStorage.removeItem('ddns_token')
        })
    }
  }, [])

  const loadHostnames = (token) => {
    axios.get(`${API_BASE}/hostnames`, { headers: { 'X-JWT-Token': token } })
      .then(res => setHostnames(res.data))
      .catch(err => console.error('Failed to load hostnames', err))
  }

  // ==================== Landing ====================
  if (view === 'landing') {
    return (
      <div className="landing">
        <div className="container">
          <h1>DDNS_Ahnlich</h1>
          <p className="tagline">Free Dynamic DNS. No nonsense.</p>
          <p>Like DuckDNS, but yours. Get a hostname like <code>yourname.ddns.dasspec.com</code> that always points to your current IP.</p>

          <div className="features">
            <div className="feature">
              <h3>Free Forever</h3>
              <p>No paid tiers. Donation supported.</p>
            </div>
            <div className="feature">
              <h3>Simple API</h3>
              <p>curl, ddclient, or any HTTP client works.</p>
            </div>
            <div className="feature">
              <h3>Your Data</h3>
              <p>Self-hosted. You own everything.</p>
            </div>
          </div>

          <div className="actions">
            <button className="btn primary" onClick={() => setView('register')}>Create Account</button>
            <button className="btn secondary" onClick={() => setView('login')}>Login</button>
          </div>

          <div className="example">
            <h3>Example update command:</h3>
            <pre><code>curl -H "apikey: YOUR_API_KEY" \
  "https://ddns.dasspec.com/api/update?hostname=myhost"</code></pre>
          </div>

          <footer>
            <p>Built by <a href="https://github.com/Crizonic-code" target="_blank">Crizonic-code</a></p>
          </footer>
        </div>
      </div>
    )
  }

  // ==================== Login ====================
  if (view === 'login') {
    return (
      <AuthForm
        title="Login"
        onSubmit={async (data) => {
          setLoading(true)
          setError('')
          try {
            const res = await axios.post(`${API_BASE}/login`, null, {
              params: { username: data.username, password: data.password }
            })
            localStorage.setItem('ddns_token', res.data.access_token)
            setUser({ username: res.data.username })
            setView('dashboard')
            loadHostnames(res.data.access_token)
          } catch (err) {
            setError(err.response?.data?.detail || 'Login failed')
          } finally {
            setLoading(false)
          }
        }}
        onBack={() => setView('landing')}
        onRegister={() => setView('register')}
        loading={loading}
        error={error}
      />
    )
  }

  // ==================== Register ====================
  if (view === 'register') {
    return (
      <AuthForm
        title="Create Account"
        showEmail={true}
        onSubmit={async (data) => {
          setLoading(true)
          setError('')
          try {
            const res = await axios.post(`${API_BASE}/register`, data)
            alert(`Account created! API Key: ${res.data.api_key}\nSave this key - you won't see it again.`)
            setView('login')
          } catch (err) {
            setError(err.response?.data?.detail || 'Registration failed')
          } finally {
            setLoading(false)
          }
        }}
        onBack={() => setView('landing')}
        onLogin={() => setView('login')}
        loading={loading}
        error={error}
      />
    )
  }

  // ==================== Dashboard ====================
  if (view === 'dashboard' && user) {
    const token = localStorage.getItem('ddns_token')
    return (
      <div className="dashboard">
        <header>
          <h2>DDNS_Ahnlich / {user.username}</h2>
          <button className="btn small" onClick={() => {
            localStorage.removeItem('ddns_token')
            setView('landing')
            setUser(null)
          }}>Logout</button>
        </header>

        <section className="api-key">
          <h3>Your API Key</h3>
          <code>{user.api_key}</code>
          <p className="hint">Use this with curl, ddclient, or any DDNS client.</p>
        </section>

        <section className="hostnames">
          <h3>Your Hostnames</h3>
          {hostnames.length === 0 ? (
            <p>No hostnames yet. Create one below.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Hostname</th>
                  <th>IP</th>
                  <th>Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {hostnames.map(h => (
                  <tr key={h.id}>
                    <td><code>{h.full_domain}</code></td>
                    <td>{h.ip_address || 'Not set'}</td>
                    <td>{h.last_updated ? new Date(h.last_updated).toLocaleString() : 'Never'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="create-hostname">
          <h3>Create New Hostname</h3>
          <form onSubmit={async (e) => {
            e.preventDefault()
            const name = e.target.hostname.value.trim()
            if (!name) return
            setLoading(true)
            try {
              const res = await axios.post(`${API_BASE}/hostnames`, { name }, {
                headers: { 'X-JWT-Token': token }
              })
              setHostnames([...hostnames, res.data])
              e.target.reset()
              alert(`Created: ${res.data.full_domain}\n\nUpdate it with:\ncurl -H "apikey: ${user.api_key}" "https://ddns.dasspec.com/api/update?hostname=${name}"`)
            } catch (err) {
              alert(err.response?.data?.detail || 'Failed to create hostname')
            } finally {
              setLoading(false)
            }
          }}>
            <input
              type="text"
              name="hostname"
              placeholder="myhost (becomes myhost.ddns.dasspec.com)"
              required
            />
            <button type="submit" className="btn primary" disabled={loading}>
              {loading ? 'Creating...' : 'Create'}
            </button>
          </form>
        </section>

        <section className="client-examples">
          <h3>Client Examples</h3>
          <pre><code>{`# curl (manual update)
curl -H "apikey: ${user.api_key}" \
  "https://ddns.dasspec.com/api/update?hostname=myhost"

# ddclient config
protocol=dyndns2
server=ddns.dasspec.com
login=myhost
password=${user.api_key}
myhost.ddns.dasspec.com

# cron (every 5 minutes)
*/5 * * * * curl -s -H "apikey: ${user.api_key}" \\
  "https://ddns.dasspec.com/api/update?hostname=myhost"`}</code></pre>
        </section>

        {error && <div className="error">{error}</div>}
      </div>
    )
  }

  return null
}

function AuthForm({ title, showEmail, onSubmit, onBack, onLogin, onRegister, loading, error }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({ username, password, email })
  }

  return (
    <div className="auth-page">
      <div className="auth-box">
        <h2>{title}</h2>
        {error && <div className="error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              minLength={3}
            />
          </div>
          <div className="field">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>
          {showEmail && (
            <div className="field">
              <label>Email (optional)</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
              />
            </div>
          )}
          <button type="submit" className="btn primary" disabled={loading}>
            {loading ? 'Please wait...' : title}
          </button>
        </form>
        <div className="auth-links">
          <button onClick={onBack} className="link">Back</button>
          {onLogin && <button onClick={onLogin} className="link">Already have an account? Login</button>}
          {onRegister && <button onClick={onRegister} className="link">Need an account? Register</button>}
        </div>
      </div>
    </div>
  )
}

export default App
