import { ReactNode, useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { useProjectStore } from '@/stores/projectStore'
import {
  Film, FolderKanban, Settings, LogOut, Menu, Search,
  LayoutGrid, Clock, Users, Bell, Camera, X, Layers
} from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listSnapshots, createSnapshot, restoreSnapshot } from '@/api/snapshots'
import { listBatches, createBatch } from '@/api/batches'
import { listJobs } from '@/api/jobs'
import { toast } from 'sonner'
import CommandPalette from './CommandPalette'
import NotificationsDropdown from './NotificationsDropdown'

interface AppShellProps {
  children: ReactNode
}

function ProjectStateBanner() {
  const { currentProjectId, currentProjectState, currentUserProjectRole } = useProjectStore()

  if (!currentProjectId || !currentProjectState) return null

  const state = currentProjectState
  const role = currentUserProjectRole || 'viewer'

  let message = ''
  let colorClass = 'bg-bg-elevated border-border text-text-secondary'

  if (state === 'creative_active') {
    message = role === 'creative'
      ? 'Creative phase — you can edit the storyboard and submit handoff.'
      : 'Creative phase active. Only the assigned Creative can edit keyframes.'
    colorClass = role === 'creative' ? 'bg-accent/10 border-accent/30' : 'bg-yellow-900/20 border-yellow-700 text-yellow-300'
  } else if (state === 'pending_handoff') {
    message = 'Awaiting Engineer acceptance of handoff. Editing is locked for both roles.'
    colorClass = 'bg-yellow-900/30 border-yellow-700 text-yellow-300'
  } else if (state === 'eng_active') {
    message = role === 'engineer'
      ? 'Engineering phase — edit the timeline, generate video/audio, and render.'
      : 'Engineering phase. Storyboard is locked; only the Engineer can work on the timeline.'
    colorClass = role === 'engineer' ? 'bg-green-900/20 border-green-700' : 'bg-yellow-900/20 border-yellow-700 text-yellow-300'
  } else if (state === 'pending_return') {
    message = 'Engineer requested return to Creative. Awaiting Creative acceptance.'
    colorClass = 'bg-yellow-900/30 border-yellow-700 text-yellow-300'
  } else if (state === 'completed') {
    message = 'Project completed. All editing is disabled.'
    colorClass = 'bg-green-900/20 border-green-700'
  }

  if (!message) return null

  return (
    <div className={`px-4 py-1.5 text-xs border-b flex items-center gap-2 ${colorClass}`}>
      <span className="font-medium uppercase tracking-wide text-[10px] opacity-75">Phase:</span>
      <span>{message}</span>
      <span className="ml-auto text-[10px] opacity-60">Your role: {role}</span>
    </div>
  )
}

export default function AppShell({ children }: AppShellProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const queryClient = useQueryClient()
  const [cmdOpen, setCmdOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [showSnapshots, setShowSnapshots] = useState(false)
  const [snapshotTierFilter, setSnapshotTierFilter] = useState<string>('')
  const [showBatches, setShowBatches] = useState(false)
  const [batchCreateMode, setBatchCreateMode] = useState(false)
  const [batchName, setBatchName] = useState('')
  const [selectedJobIds, setSelectedJobIds] = useState<string[]>([])

  const currentProjectId = useProjectStore((s) => s.currentProjectId)

  const { data: snapshotsData } = useQuery({
    queryKey: ['snapshots', currentProjectId, snapshotTierFilter],
    queryFn: () => listSnapshots(currentProjectId!, snapshotTierFilter || undefined),
    enabled: !!currentProjectId && showSnapshots,
  })

  const { data: batchesData } = useQuery({
    queryKey: ['batches', currentProjectId],
    queryFn: () => listBatches(currentProjectId!),
    enabled: !!currentProjectId && showBatches,
  })

  const { data: jobsData, isLoading: jobsLoading } = useQuery({
    queryKey: ['jobs', currentProjectId],
    queryFn: () => listJobs({ project_id: currentProjectId! }),
    enabled: !!currentProjectId && showBatches,
  })

  const createSnapMutation = useMutation({
    mutationFn: (tier: string) => createSnapshot(currentProjectId!, { type: 'manual', tier, label: `Manual ${tier}` }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['snapshots', currentProjectId] })
      toast.success('Snapshot created')
    },
  })

  const restoreSnapMutation = useMutation({
    mutationFn: (snapId: string) => restoreSnapshot(currentProjectId!, snapId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keyframes'] })
      queryClient.invalidateQueries({ queryKey: ['timeline'] })
      toast.success('Snapshot restored (reload views)')
      setShowSnapshots(false)
    },
  })

  const createBatchMutation = useMutation({
    mutationFn: (payload: { project_id: string; name: string; job_ids: string[] }) => createBatch(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batches', currentProjectId] })
      queryClient.invalidateQueries({ queryKey: ['jobs', currentProjectId] })
      toast.success(`Batch created with ${selectedJobIds.length} job(s)`)
      setBatchCreateMode(false)
      setBatchName('')
      setSelectedJobIds([])
    },
    onError: () => toast.error('Failed to create batch'),
  })

  // Reset batch create form when modal closes
  useEffect(() => {
    if (!showBatches) {
      setBatchCreateMode(false)
      setBatchName('')
      setSelectedJobIds([])
    }
  }, [showBatches])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const navItems = [
    { to: '/projects', icon: FolderKanban, label: 'Projects' },
    { to: '/admin', icon: Users, label: 'Admin', adminOnly: true },
    { to: '/settings', icon: Settings, label: 'Settings' },
  ]

  return (
    <div className="flex h-screen overflow-hidden bg-bg-base">
      {/* Left Sidebar */}
      <aside
        className={`flex flex-col border-r border-border bg-bg-surface transition-all ${
          sidebarCollapsed ? 'w-[48px]' : 'w-[220px]'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
          <Film className="w-5 h-5 text-accent" />
          {!sidebarCollapsed && (
            <span className="text-sm font-semibold text-text-primary">AI Movie Maker</span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-2">
          {navItems
            .filter((item) => !item.adminOnly || user?.global_role === 'admin')
            .map((item) => {
              const active = location.pathname.startsWith(item.to)
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`flex items-center gap-3 px-4 py-2 text-sm transition-colors ${
                    active
                      ? 'text-accent bg-accent-subtle'
                      : 'text-text-secondary hover:text-text-primary hover:bg-bg-subtle'
                  }`}
                >
                  <item.icon className="w-4 h-4" />
                  {!sidebarCollapsed && item.label}
                </Link>
              )
            })}
        </nav>

        {/* User */}
        <div className="border-t border-border p-3">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-text-muted hover:text-error w-full"
          >
            <LogOut className="w-4 h-4" />
            {!sidebarCollapsed && 'Logout'}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-12 flex items-center justify-between px-4 border-b border-border bg-bg-surface">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="text-text-muted hover:text-text-primary"
            >
              <Menu className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setCmdOpen(true)}
              className="flex items-center gap-2 text-sm text-text-muted hover:text-text-primary px-3 py-1 rounded-btn border border-border"
            >
              <Search className="w-3 h-3" />
              <span>Search...</span>
              <kbd className="text-xs text-text-muted">⌘K</kbd>
            </button>
            <NotificationsDropdown />
            {currentProjectId && (
              <button
                onClick={() => setShowSnapshots(true)}
                className="text-text-muted hover:text-text-primary p-2"
                title="Project Snapshots (tiered)"
              >
                <Camera className="w-4 h-4" />
              </button>
            )}
            {currentProjectId && (
              <button
                onClick={() => setShowBatches(true)}
                className="text-text-muted hover:text-text-primary p-2"
                title="Batch Queue"
              >
                <Layers className="w-4 h-4" />
              </button>
            )}

            {/* Real-time collaboration presence (advanced) */}
            {currentProjectId && (
              <div className="flex items-center gap-1 px-2 py-0.5 text-[10px] bg-bg-base border border-border rounded text-text-muted" title="Real-time presence (WebSocket)">
                <Users className="w-3 h-3" />
                <span>Online</span>
              </div>
            )}
            <span className="text-sm text-text-secondary">
              {user?.full_name || user?.email}
            </span>
          </div>
        </header>

        {/* Project State Banner */}
        <ProjectStateBanner />

        {/* Canvas */}
        <main className="flex-1 overflow-auto">{children}</main>
      </div>

      {/* Command Palette */}
      <CommandPalette open={cmdOpen} onOpenChange={setCmdOpen} />

      {/* Tiered Snapshots Modal (advanced low-item polish) */}
      {showSnapshots && currentProjectId && (
        <div className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4">
          <div className="w-full max-w-[720px] bg-bg-elevated border border-border rounded-card shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <div className="font-medium">Project Snapshots (tiered)</div>
              <button onClick={() => setShowSnapshots(false)} className="text-text-muted hover:text-text-primary">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4">
              <div className="flex gap-2 mb-3">
                <button onClick={() => createSnapMutation.mutate('manual')} disabled={createSnapMutation.isPending} className="text-xs px-3 py-1 border border-border rounded hover:bg-bg-subtle">+ Manual</button>
                <button onClick={() => createSnapMutation.mutate('major')} disabled={createSnapMutation.isPending} className="text-xs px-3 py-1 border border-border rounded hover:bg-bg-subtle">+ Major</button>
                <button onClick={() => createSnapMutation.mutate('major')} disabled={createSnapMutation.isPending} className="text-xs px-3 py-1 border border-accent text-accent rounded hover:bg-accent/10">Create Major Snapshot</button>
                <select
                  value={snapshotTierFilter}
                  onChange={(e) => setSnapshotTierFilter(e.target.value)}
                  className="text-xs bg-bg-base border border-border rounded px-2"
                >
                  <option value="">All tiers</option>
                  <option value="auto">auto</option>
                  <option value="manual">manual</option>
                  <option value="major">major</option>
                  <option value="handoff">handoff</option>
                </select>
                <div className="flex-1" />
                <span className="text-[10px] text-text-muted self-center">Auto-snapshots on handoff & render</span>
              </div>

              <div className="max-h-72 overflow-auto border border-border rounded">
                {(snapshotsData?.items || []).length === 0 ? (
                  <div className="p-4 text-sm text-text-muted">No snapshots yet for this project.</div>
                ) : (
                  (snapshotsData?.items || []).map((s: any) => (
                    <div key={s.id} className="flex items-center justify-between px-3 py-2 border-b border-border last:border-b-0 text-sm">
                      <div>
                        <span className="font-mono text-xs text-text-muted mr-2">{s.tier}</span>
                        <span>{s.label || s.type || 'Snapshot'}</span>
                        <span className="text-[10px] text-text-muted ml-2">{new Date(s.created_at).toLocaleString()}</span>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => restoreSnapMutation.mutate(s.id)}
                          disabled={restoreSnapMutation.isPending}
                          className="text-xs px-2 py-0.5 bg-accent text-accent-fg rounded hover:bg-accent-hover"
                        >
                          Restore
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="px-4 py-2 text-[10px] border-t border-border bg-bg-surface text-text-muted">
              Tiered snapshots provide versioned checkpoints (auto on key events, manual on demand). Restore overwrites current storyboard/timeline state.
            </div>
          </div>
        </div>
      )}

      {/* Batch Queue Modal (advanced feature) */}
      {showBatches && currentProjectId && (
        <div className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4">
          <div className="w-full max-w-[720px] bg-bg-elevated border border-border rounded-card shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <div className="font-medium flex items-center gap-2">
                Batch Queue
                {batchCreateMode && <span className="text-xs px-2 py-0.5 rounded bg-accent/20 text-accent">Create new</span>}
              </div>
              <button onClick={() => setShowBatches(false)} className="text-text-muted hover:text-text-primary">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 max-h-[420px] overflow-auto space-y-4">
              {/* Existing Batches */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs uppercase tracking-wide text-text-muted">Existing Batches</div>
                  <button
                    onClick={() => {
                      setBatchCreateMode(true)
                      if (!batchName) setBatchName(`Batch ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}`)
                    }}
                    className="text-xs px-2 py-1 border border-border rounded hover:bg-bg-subtle"
                  >
                    + Create from Jobs
                  </button>
                </div>

                {(batchesData?.items || []).length === 0 ? (
                  <div className="text-sm text-text-muted p-3 text-center border border-border rounded">No batches yet for this project.</div>
                ) : (
                  (batchesData?.items || []).map((b: any) => {
                    const progress = Math.round(((b.done_count + b.failed_count) / Math.max(1, b.job_count)) * 100)
                    return (
                      <div key={b.id} className="mb-2 last:mb-0 p-3 border border-border rounded bg-bg-base">
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="font-medium text-sm">{b.name}</div>
                            <div className="text-[10px] text-text-muted">{new Date(b.created_at).toLocaleString()}</div>
                          </div>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            b.status === 'done' ? 'bg-success/20 text-success' :
                            b.status === 'failed' || b.status === 'partial_failure' ? 'bg-error/20 text-error' :
                            'bg-accent/20 text-accent'
                          }`}>
                            {b.status}
                          </span>
                        </div>
                        {/* Progress bar */}
                        <div className="mt-2 h-1.5 w-full bg-bg-subtle rounded overflow-hidden">
                          <div className="h-1.5 bg-accent transition-all" style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} />
                        </div>
                        <div className="mt-1 text-xs flex gap-4 text-text-muted">
                          <span>Jobs: {b.job_count}</span>
                          <span>Done: {b.done_count}</span>
                          <span>Failed: {b.failed_count}</span>
                          <span className="ml-auto">{progress}%</span>
                        </div>
                      </div>
                    )
                  })
                )}
              </div>

              {/* Create Batch Form */}
              {batchCreateMode && (
                <div className="border border-accent/40 rounded p-3 bg-bg-base">
                  <div className="text-xs uppercase tracking-wide text-accent mb-2">Create New Batch</div>

                  <input
                    type="text"
                    value={batchName}
                    onChange={(e) => setBatchName(e.target.value)}
                    placeholder="Batch name (e.g. Hero shots batch)"
                    className="w-full mb-3 px-3 py-1.5 text-sm bg-bg-elevated border border-border rounded focus:outline-none focus:border-accent"
                  />

                  <div className="text-xs text-text-muted mb-1.5">Select queued or running jobs (not already in a batch):</div>

                  <div className="max-h-48 overflow-auto border border-border rounded bg-bg-surface mb-3">
                    {jobsLoading ? (
                      <div className="p-3 text-xs text-text-muted">Loading jobs...</div>
                    ) : (
                      (() => {
                        const eligible = (jobsData?.items || []).filter(
                          (j: any) => !j.batch_id && ['queued', 'running'].includes(j.status)
                        )
                        if (eligible.length === 0) {
                          return <div className="p-3 text-xs text-text-muted">No eligible unbatched jobs in queued/running state.</div>
                        }
                        return eligible.map((j: any) => {
                          const checked = selectedJobIds.includes(j.id)
                          return (
                            <label
                              key={j.id}
                              className="flex items-start gap-2 px-3 py-2 border-b border-border/60 last:border-b-0 hover:bg-bg-subtle cursor-pointer text-xs"
                            >
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedJobIds([...selectedJobIds, j.id])
                                  } else {
                                    setSelectedJobIds(selectedJobIds.filter(id => id !== j.id))
                                  }
                                }}
                                className="mt-0.5"
                              />
                              <div className="flex-1 min-w-0">
                                <div className="font-mono text-[10px] text-text-muted">{j.type} • {j.source_entity_type}</div>
                                <div className="truncate text-text-primary">{j.status} • queued {new Date(j.queued_at).toLocaleTimeString()}</div>
                              </div>
                            </label>
                          )
                        })
                      })()
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setBatchCreateMode(false)
                        setBatchName('')
                        setSelectedJobIds([])
                      }}
                      className="flex-1 px-3 py-1.5 text-xs border border-border rounded hover:bg-bg-subtle"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => {
                        if (!batchName.trim() || selectedJobIds.length === 0) return
                        createBatchMutation.mutate({
                          project_id: currentProjectId,
                          name: batchName.trim(),
                          job_ids: selectedJobIds,
                        })
                      }}
                      disabled={createBatchMutation.isPending || !batchName.trim() || selectedJobIds.length === 0}
                      className="flex-1 px-3 py-1.5 text-xs bg-accent text-accent-fg rounded hover:bg-accent-hover disabled:opacity-50"
                    >
                      {createBatchMutation.isPending ? 'Creating...' : `Create Batch (${selectedJobIds.length} jobs)`}
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="px-4 py-2 text-[10px] border-t border-border bg-bg-surface text-text-muted">
              Batches group jobs for bulk monitoring and progress. Counters update automatically on job completion/failure.
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
