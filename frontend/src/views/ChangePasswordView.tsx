import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { changePassword } from '@/api/auth'
import { KeyRound } from 'lucide-react'
import { toast } from 'sonner'

export default function ChangePasswordView() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match')
      return
    }

    setLoading(true)
    try {
      await changePassword(currentPassword, newPassword)
      // Update user state to reflect password change
      if (user) {
        setUser({ ...user, force_password_change: false })
      }
      toast.success('Password changed successfully')
      navigate('/projects')
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to change password'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-base">
      <div className="w-full max-w-sm p-8 bg-bg-surface rounded-card border border-border">
        <div className="flex items-center justify-center gap-2 mb-6">
          <KeyRound className="w-7 h-7 text-accent" />
          <h1 className="text-lg font-bold text-text-primary">Change Password</h1>
        </div>

        {user?.force_password_change && (
          <div className="mb-4 p-3 bg-warning/10 border border-warning/30 rounded-btn text-sm text-warning">
            You must change your default password before continuing.
          </div>
        )}

        <p className="text-sm text-text-secondary mb-4">
          Password must be at least 10 characters with uppercase, lowercase, digit, and special character.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-text-secondary mb-1">Current Password *</label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              className="w-full px-3 py-2 bg-bg-base border border-border rounded-btn text-text-primary text-sm focus:outline-none focus:border-accent focus:border-2"
            />
          </div>

          <div>
            <label className="block text-sm text-text-secondary mb-1">New Password *</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              className="w-full px-3 py-2 bg-bg-base border border-border rounded-btn text-text-primary text-sm focus:outline-none focus:border-accent focus:border-2"
            />
          </div>

          <div>
            <label className="block text-sm text-text-secondary mb-1">Confirm New Password *</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="w-full px-3 py-2 bg-bg-base border border-border rounded-btn text-text-primary text-sm focus:outline-none focus:border-accent focus:border-2"
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
            {loading ? 'Changing...' : 'Change Password'}
          </button>
        </form>
      </div>
    </div>
  )
}
