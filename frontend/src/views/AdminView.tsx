import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/api/client'
import { useState } from 'react'
import { Users, UserPlus, Shield, X, Check } from 'lucide-react'
import { toast } from 'sonner'

export default function AdminView() {
  const queryClient = useQueryClient()
  const [showInvite, setShowInvite] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')

  const { data: usersData, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => {
      const res = await api.get('/users/')
      return res.data
    },
  })

  const users = usersData?.users || []

  // ---- Invite mutation ----
  const inviteMutation = useMutation({
    mutationFn: async (email: string) => {
      const res = await api.post('/invites/', { email })
      return res.data
    },
    onSuccess: () => {
      toast.success('Invite sent')
      setShowInvite(false)
      setInviteEmail('')
    },
    onError: () => toast.error('Failed to send invite'),
  })

  // ---- Toggle active mutation ----
  const toggleActiveMutation = useMutation({
    mutationFn: async ({ userId, isActive }: { userId: string; isActive: boolean }) => {
      const res = await api.put(`/users/${userId}`, { is_active: isActive })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('User status updated')
    },
    onError: () => toast.error('Failed to update user status'),
  })

  // ---- Role change mutation ----
  const changeRoleMutation = useMutation({
    mutationFn: async ({ userId, role }: { userId: string; role: string }) => {
      const res = await api.put(`/users/${userId}`, { global_role: role })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('User role updated')
    },
    onError: () => toast.error('Failed to update role'),
  })

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <Shield className="w-5 h-5" /> Admin Panel
        </h1>
        <button
          onClick={() => setShowInvite(true)}
          className="flex items-center gap-2 px-3 py-2 bg-accent text-accent-fg rounded-btn text-sm hover:bg-accent-hover"
        >
          <UserPlus className="w-4 h-4" /> Invite User
        </button>
      </div>

      {/* Invite inline form */}
      {showInvite && (
        <div className="mb-6 p-4 bg-bg-surface border border-border rounded-card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-text-primary">Invite a User</h2>
            <button onClick={() => setShowInvite(false)} className="text-text-muted hover:text-text-primary">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="user@example.com"
              className="flex-1 px-3 py-2 bg-bg-base border border-border rounded-btn text-sm text-text-primary"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && inviteEmail.trim()) inviteMutation.mutate(inviteEmail.trim())
              }}
            />
            <button
              onClick={() => inviteMutation.mutate(inviteEmail.trim())}
              disabled={!inviteEmail.trim() || inviteMutation.isPending}
              className="px-3 py-2 bg-accent text-accent-fg rounded-btn text-sm hover:bg-accent-hover disabled:opacity-50"
            >
              {inviteMutation.isPending ? 'Sending...' : 'Send Invite'}
            </button>
            <button
              onClick={() => { setShowInvite(false); setInviteEmail('') }}
              className="px-3 py-2 border border-border rounded-btn text-sm text-text-secondary hover:bg-bg-subtle"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="bg-bg-surface border border-border rounded-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-3 text-text-secondary font-medium">Name</th>
              <th className="text-left px-4 py-3 text-text-secondary font-medium">Email</th>
              <th className="text-left px-4 py-3 text-text-secondary font-medium">Role</th>
              <th className="text-left px-4 py-3 text-text-secondary font-medium">Approval</th>
              <th className="text-left px-4 py-3 text-text-secondary font-medium">Status</th>
              <th className="text-left px-4 py-3 text-text-secondary font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-text-muted">Loading...</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-text-muted">No users</td></tr>
            ) : (
              users.map((user: any) => (
                <tr key={user.id} className="border-b border-border hover:bg-bg-subtle">
                  <td className="px-4 py-3 text-text-primary">{user.full_name}</td>
                  <td className="px-4 py-3 text-text-secondary">{user.email}</td>
                  {/* Role dropdown */}
                  <td className="px-4 py-3">
                    <select
                      value={user.global_role}
                      onChange={(e) =>
                        changeRoleMutation.mutate({ userId: user.id, role: e.target.value })
                      }
                      className="text-xs px-2 py-1 rounded-tag bg-bg-base border border-border text-text-primary cursor-pointer"
                    >
                      <option value="user">user</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>
                  {/* Approval state */}
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-tag ${
                      user.approval_state === 'approved'
                        ? 'bg-green-900/30 text-success'
                        : user.approval_state === 'rejected'
                          ? 'bg-red-900/30 text-error'
                          : 'bg-yellow-900/30 text-yellow-400'
                    }`}>
                      {user.approval_state || 'pending'}
                    </span>
                  </td>
                  {/* Active / Inactive */}
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-tag ${
                      user.is_active ? 'bg-green-900/30 text-success' : 'bg-red-900/30 text-error'
                    }`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  {/* Toggle active button */}
                  <td className="px-4 py-3">
                    <button
                      onClick={() =>
                        toggleActiveMutation.mutate({ userId: user.id, isActive: !user.is_active })
                      }
                      disabled={toggleActiveMutation.isPending}
                      className={`text-xs px-2.5 py-1 rounded-btn border transition-colors ${
                        user.is_active
                          ? 'border-red-700/50 text-error hover:bg-red-900/20'
                          : 'border-green-700/50 text-success hover:bg-green-900/20'
                      } disabled:opacity-50`}
                      title={user.is_active ? 'Deactivate user' : 'Activate user'}
                    >
                      {user.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
