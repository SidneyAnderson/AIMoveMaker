import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/api/client'
import { useState, useEffect } from 'react'
import { getNotificationPreferences, updateNotificationPreferences } from '@/api/notifications'
import { Settings, Pencil, Check, X, Cpu } from 'lucide-react'
import { toast } from 'sonner'
import { useProjectStore } from '@/stores/projectStore'
import { listKeyframes } from '@/api/storyboard'
import { listJobs } from '@/api/jobs'

export default function SettingsView() {
  const queryClient = useQueryClient()
  const currentProjectId = useProjectStore((s) => s.currentProjectId)
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')

  // Notification Preferences (full backend support)
  const [notifPrefs, setNotifPrefs] = useState<Record<string, boolean>>({
    job_completed: true,
    render_complete: true,
    handoff: true,
    approval: true,
    project_state_change: true,
  })

  // Load preferences from backend on mount
  useEffect(() => {
    getNotificationPreferences()
      .then((prefs) => {
        const emailPrefs = prefs.email || {}
        setNotifPrefs({
          job_completed: emailPrefs.job_completed ?? true,
          render_complete: emailPrefs.render_complete ?? true,
          handoff: emailPrefs.handoff ?? true,
          approval: emailPrefs.approval ?? true,
          project_state_change: emailPrefs.project_state_change ?? true,
        })
      })
      .catch(() => {
        // keep defaults if fetch fails
      })
  }, [])

  // Hardware Profile (advanced exposure)
  const { data: hardwareData } = useQuery({
    queryKey: ['hardware-profile'],
    queryFn: async () => {
      const res = await api.get('/hardware/')
      return res.data
    },
  })

  // Basic Project Analytics (advanced exposure)
  const { data: keyframesData } = useQuery({
    queryKey: ['keyframes-count', currentProjectId],
    queryFn: () => listKeyframes(currentProjectId!),
    enabled: !!currentProjectId,
  })
  const { data: jobsData } = useQuery({
    queryKey: ['jobs-count', currentProjectId],
    queryFn: () => listJobs({ project_id: currentProjectId! }),
    enabled: !!currentProjectId,
  })

  const { data, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      const res = await api.get('/settings/')
      return res.data
    },
  })

  const settings = data?.items || []

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

      {/* Notification Preferences (advanced feature) */}
      <div className="mt-8 bg-bg-surface border border-border rounded-card p-4">
        <h2 className="text-sm font-medium text-text-primary mb-3">Notification Preferences</h2>
        <p className="text-xs text-text-muted mb-3">
          Choose which events you want to receive in-app and email notifications for (email templates can be customized server-side).
        </p>

        <div className="space-y-2">
          {Object.entries(notifPrefs).map(([key, enabled]) => (
            <div key={key} className="flex items-center justify-between text-sm">
              <span className="text-text-primary">{key.replace(/_/g, ' ')}</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={enabled as boolean}
                  onChange={async (e) => {
                    const newFlat = { ...notifPrefs, [key]: e.target.checked }
                    setNotifPrefs(newFlat)

                    // Build nested structure for backend
                    const emailPrefs = {
                      job_completed: newFlat.job_completed,
                      render_complete: newFlat.render_complete,
                      handoff: newFlat.handoff,
                      approval: newFlat.approval,
                      project_state_change: newFlat.project_state_change,
                    }

                    try {
                      await updateNotificationPreferences({ email: emailPrefs })
                    } catch {
                      // non-fatal; UI already updated optimistically
                    }
                  }}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-bg-base peer-focus:outline-none peer-focus:ring-1 peer-focus:ring-accent rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accent"></div>
              </label>
            </div>
          ))}
        </div>
        <div className="text-[10px] text-text-muted mt-3">
          Changes are saved locally. Full server-side preferences coming soon.
        </div>
      </div>

      {/* Hardware Profile (advanced exposure of backend profiler) */}
      <div className="mt-8 bg-bg-surface border border-border rounded-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Cpu className="w-4 h-4" />
          <h2 className="text-sm font-medium text-text-primary">Hardware Profile</h2>
        </div>

        {hardwareData ? (
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <div className="text-text-muted">GPU Class</div>
            <div className="font-mono text-xs text-text-primary">{hardwareData.gpu_class}</div>

            <div className="text-text-muted">Device</div>
            <div className="font-mono text-xs text-text-primary truncate">{hardwareData.device_name}</div>

            <div className="text-text-muted">VRAM</div>
            <div className="font-mono text-xs text-text-primary">
              {hardwareData.vram_total_mb} MB total / {hardwareData.vram_free_mb} MB free
            </div>

            <div className="text-text-muted">Precision</div>
            <div className="font-mono text-xs text-text-primary">{hardwareData.precision}</div>

            <div className="text-text-muted">Optimizations</div>
            <div className="text-xs text-text-primary">
              xformers: {hardwareData.use_xformers ? 'on' : 'off'} · compile: {hardwareData.torch_compile ? 'on' : 'off'}
            </div>
          </div>
        ) : (
          <div className="text-xs text-text-muted">Loading hardware profile...</div>
        )}
        <div className="text-[10px] text-text-muted mt-3">
          Detected at startup. Used for automatic pipeline optimization.
        </div>
      </div>

      {/* Basic Project Analytics (advanced exposure) */}
      <div className="mt-8 bg-bg-surface border border-border rounded-card p-4">
        <h2 className="text-sm font-medium text-text-primary mb-3">Project Analytics</h2>
        {!currentProjectId ? (
          <div className="text-xs text-text-muted">Open a project to see stats.</div>
        ) : (
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <div className="text-text-muted">Keyframes</div>
            <div className="font-mono text-xs text-text-primary">{keyframesData?.items?.length ?? '—'}</div>

            <div className="text-text-muted">Jobs (this project)</div>
            <div className="font-mono text-xs text-text-primary">{jobsData?.items?.length ?? '—'}</div>

            <div className="text-text-muted">Completed Jobs</div>
            <div className="font-mono text-xs text-text-primary">
              {jobsData?.items?.filter((j: any) => j.status === 'done').length ?? '—'}
            </div>
          </div>
        )}
        <div className="text-[10px] text-text-muted mt-3">
          Basic stats from current project. Full dashboard coming soon.
        </div>
      </div>
    </div>
  )
}
