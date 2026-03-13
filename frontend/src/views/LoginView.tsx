import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { login } from '@/api/auth'
import { Film } from 'lucide-react'
import { toast } from 'sonner'

export default function LoginView() {
  const navigate = useNavigate()
  const setTokens = useAuthStore((s) => s.setTokens)
  const setUser = useAuthStore((s) => s.setUser)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await login(email, password)
      setTokens(data.access_token, data.refresh_token)
      setUser(data.user)
      if (data.force_password_change) {
        toast.warning('You must change your password before continuing.')
      }
      navigate('/')
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Login failed'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-base">
      <div className="w-full max-w-sm p-8 bg-bg-surface rounded-card border border-border">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Film className="w-8 h-8 text-accent" />
          <h1 className="text-xl font-bold text-text-primary">AI Movie Maker</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-text-secondary mb-1">Email *</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 bg-bg-base border border-border rounded-btn text-text-primary text-sm focus:outline-none focus:border-accent focus:border-2"
              placeholder="admin@localhost"
            />
          </div>

          <div>
            <label className="block text-sm text-text-secondary mb-1">Password *</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 bg-bg-base border border-border rounded-btn text-text-primary text-sm focus:outline-none focus:border-accent focus:border-2"
              placeholder="Enter password"
            />
          </div>

          {error && (
            <p className="text-sm text-error">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-accent text-accent-fg rounded-btn text-sm font-medium hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
