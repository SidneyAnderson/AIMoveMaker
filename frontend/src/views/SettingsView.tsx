import { useQuery } from '@tanstack/react-query'
import api from '@/api/client'
import { Settings, Save } from 'lucide-react'

export default function SettingsView() {
  const { data, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      const res = await api.get('/settings/')
      return res.data
    },
  })

  const settings = data?.settings || []

  return (
    <div className="p-6">
      <h1 className="text-lg font-semibold text-text-primary flex items-center gap-2 mb-6">
        <Settings className="w-5 h-5" /> System Settings
      </h1>

      <div className="bg-bg-surface border border-border rounded-card">
        {isLoading ? (
          <div className="p-8 text-center text-text-muted">Loading settings...</div>
        ) : settings.length === 0 ? (
          <div className="p-8 text-center text-text-muted">No settings configured</div>
        ) : (
          <div className="divide-y divide-border">
            {settings.map((setting: any) => (
              <div key={setting.key} className="px-4 py-3 flex items-center justify-between">
                <div>
                  <p className="text-sm text-text-primary font-medium">{setting.key}</p>
                  <p className="text-xs text-text-muted mt-0.5">{setting.description || 'No description'}</p>
                </div>
                <div className="text-sm text-text-secondary font-mono">
                  {setting.is_secret ? '••••••••' : setting.value}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
