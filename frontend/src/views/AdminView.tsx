import { useQuery } from '@tanstack/react-query'
import api from '@/api/client'
import { Users, UserPlus, Shield } from 'lucide-react'

export default function AdminView() {
  const { data: usersData, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => {
      const res = await api.get('/users/')
      return res.data
    },
  })

  const users = usersData?.users || []

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <Shield className="w-5 h-5" /> Admin Panel
        </h1>
        <button className="flex items-center gap-2 px-3 py-2 bg-accent text-accent-fg rounded-btn text-sm hover:bg-accent-hover">
          <UserPlus className="w-4 h-4" /> Invite User
        </button>
      </div>

      <div className="bg-bg-surface border border-border rounded-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-3 text-text-secondary font-medium">Name</th>
              <th className="text-left px-4 py-3 text-text-secondary font-medium">Email</th>
              <th className="text-left px-4 py-3 text-text-secondary font-medium">Role</th>
              <th className="text-left px-4 py-3 text-text-secondary font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-text-muted">Loading...</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-text-muted">No users</td></tr>
            ) : (
              users.map((user: any) => (
                <tr key={user.id} className="border-b border-border hover:bg-bg-subtle">
                  <td className="px-4 py-3 text-text-primary">{user.full_name}</td>
                  <td className="px-4 py-3 text-text-secondary">{user.email}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs px-2 py-0.5 rounded-tag bg-accent-subtle text-accent">
                      {user.global_role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-tag ${
                      user.is_active ? 'bg-green-900/30 text-success' : 'bg-red-900/30 text-error'
                    }`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
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
