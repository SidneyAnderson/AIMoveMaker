import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/api/client'
import { useState } from 'react'
import { Settings, Pencil, Check, X } from 'lucide-react'
import { toast } from 'sonner'

export default function SettingsView() {
  const queryClient = useQueryClient()
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      const res = await api.get('/settings/')
      return res.data
    },
  })

  const settings = data?.settings || []

  const saveMutation = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: string }) => {
      const res = await api.put(`/settings/${key}`, { value })
      return res.data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setEditingKey(null)
      setEditValue('')
      toast.success(`Setting "${variables.key}" saved`)
    },
    onError: (_err, variables) => toast.error(`Failed to save "${variables.key}"`),
  })

  const startEditing = (setting: any) => {
    setEditingKey(setting.key)
    // For secrets, start with an empty field so the user types the new value
    setEditValue(setting.is_secret ? '' : (setting.value ?? ''))
  }

  const cancelEditing = () => {
    setEditingKey(null)
    setEditValue('')
  }

  const handleSave = (key: string) => {
    saveMutation.mutate({ key, value: editValue })
  }

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
            {settings.map((setting: any) => {
              const isEditing = editingKey === setting.key
              return (
                <div key={setting.key} className="px-4 py-3 flex items-center justify-between gap-4">
                  {/* Left: key + description */}
                  <div className="min-w-0 flex-shrink">
                    <p className="text-sm text-text-primary font-medium">{setting.key}</p>
                    <p className="text-xs text-text-muted mt-0.5">{setting.description || 'No description'}</p>
                  </div>

                  {/* Right: value display or edit input */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {isEditing ? (
                      <>
                        <input
                          type={setting.is_secret ? 'password' : 'text'}
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          placeholder={setting.is_secret ? 'Enter new value...' : ''}
                          className="px-2 py-1 bg-bg-base border border-border rounded-btn text-sm text-text-primary font-mono w-64"
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSave(setting.key)
                            if (e.key === 'Escape') cancelEditing()
                          }}
                        />
                        <button
                          onClick={() => handleSave(setting.key)}
                          disabled={saveMutation.isPending}
                          className="p-1 text-success hover:bg-green-900/20 rounded disabled:opacity-50"
                          title="Save"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                        <button
                          onClick={cancelEditing}
                          className="p-1 text-text-muted hover:bg-bg-subtle rounded"
                          title="Cancel"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </>
                    ) : (
                      <>
                        <span className="text-sm text-text-secondary font-mono max-w-xs truncate">
                          {setting.is_secret ? '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022' : (setting.value ?? '')}
                        </span>
                        <button
                          onClick={() => startEditing(setting)}
                          className="p-1 text-text-muted hover:text-accent hover:bg-bg-subtle rounded"
                          title="Edit"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
