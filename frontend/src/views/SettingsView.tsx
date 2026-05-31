import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/api/client'
import { useState, useEffect } from 'react'
import { getNotificationPreferences, updateNotificationPreferences } from '@/api/notifications'
import { Settings, Pencil, Check, X, Cpu, HardDrive, Gauge, AlertTriangle, CheckCircle, RefreshCw, Play, BarChart3, Clock, TrendingUp, XCircle, AlertCircle } from 'lucide-react'
import { getErrorInfo } from '@/lib/errorCatalog'
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

  // Hardware Profile + VRAM tools (advanced #7)
  const { data: hardwareData, isLoading: hwLoading } = useQuery({
    queryKey: ['hardware-profile'],
    queryFn: async () => {
      const res = await api.get('/hardware/')
      return res.data
    },
  })

  // Models for recommendations (active only)
  const { data: modelsData } = useQuery({
    queryKey: ['models-for-recs'],
    queryFn: async () => {
      const res = await api.get('/models/', { params: { limit: 200 } })
      return res.data
    },
  })

  // Estimator form state
  const [estModelFloor, setEstModelFloor] = useState(2048)
  const [estWidth, setEstWidth] = useState(512)
  const [estHeight, setEstHeight] = useState(512)
  const [estFrames, setEstFrames] = useState(1)
  const [estLoras, setEstLoras] = useState(0)
  const [estPrecision, setEstPrecision] = useState<'fp16' | 'bf16' | 'fp32'>('fp16')
  const [estResult, setEstResult] = useState<any>(null)
  const [estLoading, setEstLoading] = useState(false)

  const runEstimator = async () => {
    setEstLoading(true)
    try {
      const res = await api.get('/hardware/estimate', {
        params: {
          model_vram_floor_mb: estModelFloor,
          width: estWidth,
          height: estHeight,
          frames: estFrames,
          lora_count: estLoras,
          precision: estPrecision,
        },
      })
      setEstResult(res.data)
    } catch (e) {
      toast.error('Estimator failed')
    } finally {
      setEstLoading(false)
    }
  }

  // Quick model select for estimator
  const handleModelSelect = (floor: number) => {
    setEstModelFloor(floor)
    setEstResult(null)
  }

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

  // Advanced Analytics computations (client-side from existing data, no new backend)
  const analytics = (() => {
    const jobs: any[] = jobsData?.items || []
    if (jobs.length === 0) return null

    const total = jobs.length
    const done = jobs.filter(j => j.status === 'done').length
    const failed = jobs.filter(j => j.status === 'failed').length
    const cancelled = jobs.filter(j => j.status === 'cancelled').length
    const running = jobs.filter(j => j.status === 'running').length
    const queued = jobs.filter(j => j.status === 'queued').length

    const successRate = total > 0 ? Math.round((done / (done + failed || 1)) * 100) : 0

    // Duration calc for completed jobs (in minutes)
    const completedJobs = jobs.filter(j => j.status === 'done' && j.started_at && j.completed_at)
    let avgDurationMin = 0
    if (completedJobs.length > 0) {
      const durations = completedJobs.map(j => {
        const start = new Date(j.started_at).getTime()
        const end = new Date(j.completed_at).getTime()
        return (end - start) / 1000 / 60
      })
      avgDurationMin = Math.round(durations.reduce((a, b) => a + b, 0) / durations.length)
    }

    // By type
    const byType: Record<string, number> = {}
    jobs.forEach(j => {
      byType[j.type] = (byType[j.type] || 0) + 1
    })

    // By status
    const byStatus = { queued, running, done, failed, cancelled }

    // By GPU target
    const local = jobs.filter(j => j.gpu_target === 'local').length
    const vastai = jobs.filter(j => j.gpu_target === 'vastai').length

    // Recent activity (last 10 jobs by queued time)
    const recent = [...jobs]
      .sort((a, b) => new Date(b.queued_at).getTime() - new Date(a.queued_at).getTime())
      .slice(0, 10)

    // Total estimated VRAM requested
    const totalVramEst = jobs.reduce((sum, j) => sum + (j.vram_estimate_mb || 0), 0)

    // Failure reasons
    const failureReasons: Record<string, number> = {}
    jobs.filter(j => j.status === 'failed' && j.error_code).forEach(j => {
      failureReasons[j.error_code] = (failureReasons[j.error_code] || 0) + 1
    })

    return {
      total, done, failed, successRate, avgDurationMin,
      byType, byStatus, local, vastai, recent, totalVramEst, failureReasons
    }
  })()

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

      {/* Hardware Profile + VRAM Tools (advanced #7) */}
      <div className="mt-8 bg-bg-surface border border-border rounded-card p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-accent" />
            <h2 className="text-sm font-medium text-text-primary">Hardware Profile & VRAM Tools</h2>
          </div>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['hardware-profile'] })}
            className="flex items-center gap-1 px-2 py-0.5 text-xs border border-border rounded hover:bg-bg-subtle"
            title="Refresh profile"
          >
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
        </div>

        {hwLoading && !hardwareData ? (
          <div className="text-xs text-text-muted">Detecting GPU...</div>
        ) : hardwareData ? (
          <>
            {/* Enhanced Profile Card */}
            <div className="mb-4 p-3 bg-bg-base border border-border rounded">
              <div className="flex items-baseline justify-between mb-2">
                <div>
                  <span className="font-semibold text-text-primary">{hardwareData.device_name}</span>
                  <span className="ml-2 text-xs px-2 py-0.5 rounded bg-accent/20 text-accent font-mono">{hardwareData.gpu_class}</span>
                </div>
                <div className="text-xs text-text-muted font-mono">
                  CC {hardwareData.compute_capability?.join?.('.') || '—'}
                </div>
              </div>

              {/* VRAM Usage Bar */}
              <div className="mb-2">
                <div className="flex justify-between text-[10px] text-text-muted mb-0.5">
                  <span>VRAM</span>
                  <span>{hardwareData.vram_free_mb} MB free / {hardwareData.vram_total_mb} MB total</span>
                </div>
                <div className="h-2.5 bg-bg-subtle rounded overflow-hidden">
                  <div
                    className="h-2.5 bg-accent transition-all"
                    style={{
                      width: `${Math.min(100, Math.max(5, Math.round(((hardwareData.vram_total_mb - hardwareData.vram_free_mb) / Math.max(1, hardwareData.vram_total_mb)) * 100)))}%`
                    }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mt-2">
                <div className="text-text-muted">Precision</div>
                <div className="font-mono text-text-primary">{hardwareData.precision}</div>

                <div className="text-text-muted">Optimizations</div>
                <div className="flex flex-wrap gap-1">
                  <span className={`px-1.5 py-px rounded text-[10px] ${hardwareData.use_xformers ? 'bg-success/20 text-success' : 'bg-error/20 text-error'}`}>
                    xformers {hardwareData.use_xformers ? 'on' : 'off'}
                  </span>
                  <span className={`px-1.5 py-px rounded text-[10px] ${hardwareData.torch_compile ? 'bg-success/20 text-success' : 'bg-error/20 text-error'}`}>
                    compile {hardwareData.torch_compile ? 'on' : 'off'}
                  </span>
                  <span className="px-1.5 py-px rounded text-[10px] bg-bg-elevated text-text-muted font-mono">
                    {hardwareData.compile_backend}
                  </span>
                </div>
              </div>
            </div>

            {/* Model Recommendations (computed client-side from real vram_floors) */}
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-2 text-xs uppercase tracking-wide text-text-muted">
                <Gauge className="w-3.5 h-3.5" /> Model Recommendations (based on current free VRAM)
              </div>
              {modelsData?.items?.length ? (
                (() => {
                  const free = hardwareData.vram_free_mb || 0
                  const safe: any[] = []
                  const caution: any[] = []
                  const high: any[] = []

                  for (const m of modelsData.items) {
                    const floor = m.vram_floor_mb || 0
                    if (floor + 1200 < free * 0.82) safe.push(m)
                    else if (floor < free * 1.1) caution.push(m)
                    else high.push(m)
                  }

                  return (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
                      <div className="p-2 border border-success/40 bg-success/5 rounded">
                        <div className="font-medium text-success mb-1 flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Safe ({safe.length})</div>
                        {safe.slice(0, 4).map((m: any) => (
                          <div key={m.id} className="truncate text-text-primary/90" onClick={() => handleModelSelect(m.vram_floor_mb)} title="Click to use in estimator">
                            {m.display_name || m.name} <span className="text-[10px] text-text-muted">({m.vram_floor_mb}MB)</span>
                          </div>
                        ))}
                        {safe.length === 0 && <div className="text-text-muted">No fully safe models</div>}
                      </div>
                      <div className="p-2 border border-yellow-600/40 bg-yellow-900/10 rounded">
                        <div className="font-medium text-yellow-400 mb-1 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Caution ({caution.length})</div>
                        {caution.slice(0, 3).map((m: any) => (
                          <div key={m.id} className="truncate text-text-primary/90" onClick={() => handleModelSelect(m.vram_floor_mb)}>
                            {m.display_name || m.name} <span className="text-[10px] text-text-muted">({m.vram_floor_mb}MB)</span>
                          </div>
                        ))}
                      </div>
                      <div className="p-2 border border-error/40 bg-error/5 rounded">
                        <div className="font-medium text-error mb-1">High VRAM ({high.length})</div>
                        {high.slice(0, 2).map((m: any) => (
                          <div key={m.id} className="truncate text-text-primary/90" onClick={() => handleModelSelect(m.vram_floor_mb)}>
                            {m.display_name || m.name}
                          </div>
                        ))}
                        {high.length > 0 && <div className="text-[10px] text-error/80 mt-0.5">Consider Vast.ai or lower settings</div>}
                      </div>
                    </div>
                  )
                })()
              ) : (
                <div className="text-xs text-text-muted">Loading model registry for recommendations…</div>
              )}
              <div className="text-[10px] text-text-muted mt-1">Click any model name to load its VRAM floor into the estimator below.</div>
            </div>

            {/* Live VRAM Estimator Tool */}
            <div className="border border-accent/30 rounded p-3 bg-bg-base">
              <div className="flex items-center gap-2 mb-2 text-xs font-medium text-accent">
                <Play className="w-3.5 h-3.5" /> Quick VRAM Estimator (uses real backend logic)
              </div>

              <div className="grid grid-cols-2 md:grid-cols-6 gap-2 text-xs mb-3">
                <div>
                  <div className="text-text-muted mb-0.5">Base floor (MB)</div>
                  <input type="number" value={estModelFloor} onChange={e => setEstModelFloor(parseInt(e.target.value) || 2048)} className="w-full bg-bg-elevated border border-border rounded px-2 py-1 font-mono text-sm" />
                </div>
                <div>
                  <div className="text-text-muted mb-0.5">Width</div>
                  <input type="number" value={estWidth} onChange={e => setEstWidth(parseInt(e.target.value) || 512)} className="w-full bg-bg-elevated border border-border rounded px-2 py-1 font-mono text-sm" />
                </div>
                <div>
                  <div className="text-text-muted mb-0.5">Height</div>
                  <input type="number" value={estHeight} onChange={e => setEstHeight(parseInt(e.target.value) || 512)} className="w-full bg-bg-elevated border border-border rounded px-2 py-1 font-mono text-sm" />
                </div>
                <div>
                  <div className="text-text-muted mb-0.5">Frames</div>
                  <input type="number" value={estFrames} onChange={e => setEstFrames(parseInt(e.target.value) || 1)} className="w-full bg-bg-elevated border border-border rounded px-2 py-1 font-mono text-sm" />
                </div>
                <div>
                  <div className="text-text-muted mb-0.5">LoRAs</div>
                  <input type="number" value={estLoras} onChange={e => setEstLoras(parseInt(e.target.value) || 0)} className="w-full bg-bg-elevated border border-border rounded px-2 py-1 font-mono text-sm" />
                </div>
                <div>
                  <div className="text-text-muted mb-0.5">Precision</div>
                  <select value={estPrecision} onChange={e => setEstPrecision(e.target.value as any)} className="w-full bg-bg-elevated border border-border rounded px-2 py-1 text-sm">
                    <option value="fp16">fp16</option>
                    <option value="bf16">bf16</option>
                    <option value="fp32">fp32</option>
                  </select>
                </div>
              </div>

              <div className="flex gap-2 mb-2">
                <button
                  onClick={runEstimator}
                  disabled={estLoading}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs bg-accent text-accent-fg rounded hover:bg-accent-hover disabled:opacity-60"
                >
                  {estLoading ? 'Estimating…' : 'Estimate VRAM Usage'}
                </button>
                {modelsData?.items && (
                  <select onChange={(e) => { if (e.target.value) handleModelSelect(parseInt(e.target.value)) }} className="text-xs bg-bg-elevated border border-border rounded px-2">
                    <option value="">Quick load model floor…</option>
                    {modelsData.items.slice(0, 12).map((m: any) => (
                      <option key={m.id} value={m.vram_floor_mb}>{m.display_name || m.name} ({m.vram_floor_mb}MB)</option>
                    ))}
                  </select>
                )}
              </div>

              {estResult && (
                <div className={`p-2 rounded text-xs border ${estResult.is_sufficient ? 'border-success/40 bg-success/10' : 'border-error/40 bg-error/10'}`}>
                  <div className="font-mono text-base text-text-primary">
                    Est. {Math.round(estResult.estimated_mb / 1024 * 10) / 10} GB
                    <span className={`ml-2 text-xs px-1.5 py-px rounded ${estResult.is_sufficient ? 'bg-success/20 text-success' : 'bg-error/20 text-error'}`}>
                      {estResult.is_sufficient ? 'Fits comfortably' : 'Exceeds local VRAM'}
                    </span>
                  </div>
                  <div className="text-text-muted mt-0.5">
                    Available after margin: {estResult.effective_available_mb} MB • Safety margin applied
                  </div>
                  {!estResult.is_sufficient && (
                    <div className="text-error/90 mt-1">Suggestion: lower resolution/frames, fewer LoRAs, or route via Vast.ai.</div>
                  )}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="text-xs text-text-muted">Hardware profile unavailable (running CPU-only?)</div>
        )}

        <div className="text-[10px] text-text-muted mt-3">
          Profile detected at startup. Estimator & recommendations use the exact same math as job VRAM gating.
        </div>
      </div>

      {/* Advanced Project Analytics (gap #8) */}
      <div className="mt-8 bg-bg-surface border border-border rounded-card p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-accent" />
            <h2 className="text-sm font-medium text-text-primary">Project Analytics</h2>
          </div>
          <button
            onClick={() => {
              queryClient.invalidateQueries({ queryKey: ['jobs-count', currentProjectId] })
              queryClient.invalidateQueries({ queryKey: ['keyframes-count', currentProjectId] })
            }}
            className="flex items-center gap-1 px-2 py-0.5 text-xs border border-border rounded hover:bg-bg-subtle"
          >
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
        </div>

        {!currentProjectId ? (
          <div className="text-xs text-text-muted">Open a project to see stats.</div>
        ) : !analytics ? (
          <div className="text-xs text-text-muted">No jobs yet for this project.</div>
        ) : (
          <div className="space-y-5">
            {/* KPI Row */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <div className="bg-bg-base border border-border rounded p-2">
                <div className="text-[10px] text-text-muted">Total Jobs</div>
                <div className="text-2xl font-semibold text-text-primary font-mono">{analytics.total}</div>
              </div>
              <div className="bg-bg-base border border-border rounded p-2">
                <div className="text-[10px] text-text-muted flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Success Rate</div>
                <div className={`text-2xl font-semibold font-mono ${analytics.successRate > 85 ? 'text-success' : analytics.successRate > 60 ? 'text-yellow-400' : 'text-error'}`}>
                  {analytics.successRate}%
                </div>
              </div>
              <div className="bg-bg-base border border-border rounded p-2">
                <div className="text-[10px] text-text-muted flex items-center gap-1"><Clock className="w-3 h-3" /> Avg Duration</div>
                <div className="text-2xl font-semibold text-text-primary font-mono">{analytics.avgDurationMin || '—'}<span className="text-xs">min</span></div>
              </div>
              <div className="bg-bg-base border border-border rounded p-2">
                <div className="text-[10px] text-text-muted">Active / Queued</div>
                <div className="text-xl font-semibold text-accent font-mono">{analytics.byStatus.running + analytics.byStatus.queued}</div>
              </div>
              <div className="bg-bg-base border border-border rounded p-2">
                <div className="text-[10px] text-text-muted">Total VRAM Est.</div>
                <div className="text-xl font-semibold text-text-primary font-mono">{Math.round(analytics.totalVramEst / 1024)} GB</div>
              </div>
            </div>

            {/* Status Breakdown - CSS Bar Chart */}
            <div>
              <div className="text-xs text-text-muted mb-1.5 flex items-center gap-1"><TrendingUp className="w-3 h-3" /> Status Breakdown</div>
              {Object.entries(analytics.byStatus).map(([status, count]) => {
                const pct = Math.round((count / analytics.total) * 100)
                const color = status === 'done' ? 'bg-success' : status === 'failed' ? 'bg-error' : status === 'running' ? 'bg-accent' : 'bg-text-muted'
                return (
                  <div key={status} className="flex items-center gap-2 text-xs mb-1">
                    <div className="w-16 text-right text-text-muted capitalize">{status}</div>
                    <div className="flex-1 h-3 bg-bg-subtle rounded overflow-hidden">
                      <div className={`h-3 ${color} transition-all`} style={{ width: `${pct}%` }} />
                    </div>
                    <div className="w-12 font-mono text-right text-text-primary">{count} <span className="text-text-muted">({pct}%)</span></div>
                  </div>
                )
              })}
            </div>

            {/* Type Breakdown */}
            <div>
              <div className="text-xs text-text-muted mb-1.5">By Job Type</div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                {Object.entries(analytics.byType).sort((a, b) => b[1] - a[1]).map(([type, count]) => {
                  const pct = Math.round((count / analytics.total) * 100)
                  return (
                    <div key={type} className="flex justify-between bg-bg-base border border-border px-2 py-1 rounded font-mono">
                      <span className="text-text-primary truncate">{type}</span>
                      <span className="text-text-muted">{count} <span className="opacity-60">({pct}%)</span></span>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* GPU Target + Failures */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-text-muted mb-1.5">GPU Target</div>
                <div className="flex gap-2 text-xs">
                  <div className="flex-1 bg-bg-base border border-border rounded p-2">
                    Local: <span className="font-mono text-accent">{analytics.local}</span>
                  </div>
                  <div className="flex-1 bg-bg-base border border-border rounded p-2">
                    Vast.ai: <span className="font-mono text-accent">{analytics.vastai}</span>
                  </div>
                </div>
              </div>

              {Object.keys(analytics.failureReasons).length > 0 && (
                <div>
                  <div className="text-xs text-text-muted mb-1.5 flex items-center gap-1"><XCircle className="w-3 h-3 text-error" /> Top Failure Reasons</div>
                  <div className="text-xs space-y-1">
                    {Object.entries(analytics.failureReasons).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([code, count]) => {
                      const info = getErrorInfo(code);
                      return (
                        <div key={code} className="bg-error/10 border border-error/30 px-2 py-1 rounded" title={info.userMessage}>
                          <div className="flex justify-between">
                            <span className="font-medium text-error">{info.title}</span>
                            <span className="font-mono text-error/70">{count}×</span>
                          </div>
                          <div className="text-[10px] text-text-muted mt-0.5 line-clamp-1">{info.suggestedAction}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Recent Activity Mini Timeline */}
            <div>
              <div className="text-xs text-text-muted mb-1.5">Recent Activity (last {analytics.recent.length} jobs)</div>
              <div className="flex gap-px h-6 bg-bg-subtle rounded overflow-hidden">
                {analytics.recent.map((j, idx) => {
                  const color = j.status === 'done' ? 'bg-success' : j.status === 'failed' ? 'bg-error' : j.status === 'running' ? 'bg-accent' : 'bg-text-muted/60'
                  return <div key={idx} className={`${color} flex-1`} title={`${j.type} • ${j.status}`} />
                })}
              </div>
              <div className="text-[10px] text-text-muted mt-1 flex justify-between">
                <span>Oldest</span><span>Newest (most recent on right)</span>
              </div>
            </div>
          </div>
        )}

        <div className="text-[10px] text-text-muted mt-3">
          All metrics computed client-side from the job list. Success rate excludes cancelled jobs.
        </div>
      </div>
    </div>
  )
}
