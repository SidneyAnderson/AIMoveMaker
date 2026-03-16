import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listKeyframes, createKeyframe, deleteKeyframe } from '@/api/storyboard'
import { useProjectStore } from '@/stores/projectStore'
import { useEffect, useState } from 'react'
import { ImagePlus, Wand2, Send, Plus, Trash2, X } from 'lucide-react'
import { toast } from 'sonner'

interface KeyframeFormData {
  prompt: string
  negative_prompt: string
  model_id: string
  steps: number
  cfg_scale: number
  width: number
  height: number
}

const defaultForm: KeyframeFormData = {
  prompt: '',
  negative_prompt: '',
  model_id: '',
  steps: 30,
  cfg_scale: 7.5,
  width: 512,
  height: 512,
}

export default function StoryboardView() {
  const { projectId } = useParams<{ projectId: string }>()
  const queryClient = useQueryClient()
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject)
  const selectedKeyframeId = useProjectStore((s) => s.selectedKeyframeId)
  const setSelectedKeyframe = useProjectStore((s) => s.setSelectedKeyframe)

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<KeyframeFormData>({ ...defaultForm })

  useEffect(() => {
    if (projectId) setCurrentProject(projectId)
    return () => setCurrentProject(null)
  }, [projectId])

  const { data, isLoading } = useQuery({
    queryKey: ['keyframes', projectId],
    queryFn: () => listKeyframes(projectId!),
    enabled: !!projectId,
  })

  const keyframes: any[] = data?.items || []
  const selectedKeyframe = keyframes.find((kf: any) => kf.id === selectedKeyframeId)

  const createMutation = useMutation({
    mutationFn: (formData: KeyframeFormData) => {
      const payload: Record<string, unknown> = { prompt: formData.prompt }
      if (formData.negative_prompt) payload.negative_prompt = formData.negative_prompt
      if (formData.model_id) payload.model_id = formData.model_id
      if (formData.steps) payload.steps = formData.steps
      if (formData.cfg_scale) payload.cfg_scale = formData.cfg_scale
      if (formData.width) payload.width = formData.width
      if (formData.height) payload.height = formData.height
      return createKeyframe(projectId!, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keyframes', projectId] })
      setShowForm(false)
      setForm({ ...defaultForm })
      toast.success('Keyframe created')
    },
    onError: () => toast.error('Failed to create keyframe'),
  })

  const deleteMutation = useMutation({
    mutationFn: (keyframeId: string) => deleteKeyframe(projectId!, keyframeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keyframes', projectId] })
      if (selectedKeyframeId) setSelectedKeyframe(null)
      toast.success('Keyframe deleted')
    },
    onError: () => toast.error('Failed to delete keyframe'),
  })

  const handleSubmit = () => {
    if (!form.prompt.trim()) {
      toast.error('Prompt is required')
      return
    }
    createMutation.mutate(form)
  }

  return (
    <div className="h-full flex">
      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="h-10 flex items-center justify-between px-4 border-b border-border bg-bg-surface">
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted">Zoom:</span>
            {['12', '6', '3', '1'].map((z) => (
              <button key={z} className="text-xs px-2 py-1 rounded-tag text-text-secondary hover:bg-bg-subtle">
                {z}-up
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-1 px-3 py-1.5 bg-accent text-accent-fg rounded-btn text-xs hover:bg-accent-hover"
            >
              <Plus className="w-3 h-3" /> Add Keyframe
            </button>
            <button className="flex items-center gap-1 px-3 py-1.5 bg-accent text-accent-fg rounded-btn text-xs hover:bg-accent-hover">
              <Wand2 className="w-3 h-3" /> Generate All
            </button>
            <button className="flex items-center gap-1 px-3 py-1.5 bg-accent text-accent-fg rounded-btn text-xs hover:bg-accent-hover">
              <Send className="w-3 h-3" /> Submit to Engineering
            </button>
          </div>
        </div>

        {/* Inline create form */}
        {showForm && (
          <div className="border-b border-border bg-bg-surface p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-text-primary">New Keyframe</h3>
              <button onClick={() => setShowForm(false)} className="text-text-muted hover:text-text-primary">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="text-xs text-text-secondary block mb-1">Prompt *</label>
                <textarea
                  value={form.prompt}
                  onChange={(e) => setForm({ ...form, prompt: e.target.value })}
                  placeholder="Describe the keyframe image..."
                  className="w-full px-3 py-2 bg-bg-base border border-border rounded-btn text-sm text-text-primary resize-none"
                  rows={2}
                />
              </div>
              <div className="col-span-2">
                <label className="text-xs text-text-secondary block mb-1">Negative Prompt</label>
                <input
                  value={form.negative_prompt}
                  onChange={(e) => setForm({ ...form, negative_prompt: e.target.value })}
                  placeholder="What to avoid..."
                  className="w-full px-3 py-2 bg-bg-base border border-border rounded-btn text-sm text-text-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary block mb-1">Model ID</label>
                <input
                  value={form.model_id}
                  onChange={(e) => setForm({ ...form, model_id: e.target.value })}
                  placeholder="e.g. stable-diffusion-xl"
                  className="w-full px-3 py-2 bg-bg-base border border-border rounded-btn text-sm text-text-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary block mb-1">Steps</label>
                <input
                  type="number"
                  value={form.steps}
                  onChange={(e) => setForm({ ...form, steps: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 bg-bg-base border border-border rounded-btn text-sm text-text-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary block mb-1">CFG Scale</label>
                <input
                  type="number"
                  step="0.5"
                  value={form.cfg_scale}
                  onChange={(e) => setForm({ ...form, cfg_scale: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-2 bg-bg-base border border-border rounded-btn text-sm text-text-primary"
                />
              </div>
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="text-xs text-text-secondary block mb-1">Width</label>
                  <input
                    type="number"
                    step="64"
                    value={form.width}
                    onChange={(e) => setForm({ ...form, width: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-bg-base border border-border rounded-btn text-sm text-text-primary"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-xs text-text-secondary block mb-1">Height</label>
                  <input
                    type="number"
                    step="64"
                    value={form.height}
                    onChange={(e) => setForm({ ...form, height: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-bg-base border border-border rounded-btn text-sm text-text-primary"
                  />
                </div>
              </div>
            </div>
            <div className="flex gap-2 mt-3">
              <button
                onClick={handleSubmit}
                disabled={!form.prompt.trim() || createMutation.isPending}
                className="px-3 py-1.5 bg-accent text-accent-fg rounded-btn text-sm disabled:opacity-50 hover:bg-accent-hover"
              >
                {createMutation.isPending ? 'Creating...' : 'Create Keyframe'}
              </button>
              <button
                onClick={() => { setShowForm(false); setForm({ ...defaultForm }) }}
                className="px-3 py-1.5 border border-border rounded-btn text-sm text-text-secondary hover:bg-bg-subtle"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Grid */}
        <div className="flex-1 overflow-auto p-4">
          {isLoading ? (
            <div className="text-text-muted text-sm">Loading keyframes...</div>
          ) : keyframes.length === 0 ? (
            <div className="text-center py-16 text-text-muted">
              <ImagePlus className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>No keyframes yet. Add one to start your storyboard.</p>
              <button
                onClick={() => setShowForm(true)}
                className="mt-3 px-3 py-1.5 border border-dashed border-border rounded-btn text-xs hover:border-border-strong"
              >
                + Add Keyframe
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-6 gap-3">
              {keyframes.map((kf: any, idx: number) => (
                <div
                  key={kf.id}
                  onClick={() => setSelectedKeyframe(kf.id)}
                  onContextMenu={(e) => {
                    e.preventDefault()
                    if (confirm('Delete this keyframe?')) {
                      deleteMutation.mutate(kf.id)
                    }
                  }}
                  className={`bg-bg-surface border rounded-card overflow-hidden cursor-pointer transition-all group ${
                    selectedKeyframeId === kf.id
                      ? 'border-accent border-2 bg-accent-subtle'
                      : 'border-border hover:border-border-strong'
                  }`}
                >
                  {/* Thumbnail area */}
                  <div className="aspect-square bg-bg-subtle relative">
                    {kf.thumbnail_asset_id ? (
                      <div className="w-full h-full flex items-center justify-center text-text-muted text-xs">
                        Asset
                      </div>
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <ImagePlus className="w-6 h-6 text-text-muted opacity-30" />
                      </div>
                    )}
                    <span className="absolute top-1 left-1 text-[10px] bg-bg-base/80 px-1 rounded">
                      {String((kf.order_index ?? idx) + 1).padStart(2, '0')}
                    </span>
                    <span className={`absolute top-1 right-1 w-2 h-2 rounded-full ${
                      kf.thumbnail_asset_id ? 'bg-success' : 'bg-text-muted'
                    }`} />
                    {/* Delete button on hover */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        if (confirm('Delete this keyframe?')) {
                          deleteMutation.mutate(kf.id)
                        }
                      }}
                      className="absolute bottom-1 right-1 p-1 bg-bg-base/80 rounded opacity-0 group-hover:opacity-100 transition-opacity hover:bg-error/20"
                    >
                      <Trash2 className="w-3 h-3 text-error" />
                    </button>
                  </div>
                  {/* Info */}
                  <div className="p-2">
                    <p className="text-xs text-text-secondary truncate">
                      {kf.prompt || 'No prompt'}
                    </p>
                    <p className="text-[10px] text-text-muted mt-0.5 truncate">
                      {kf.model_id || 'No model'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Detail side panel */}
      {selectedKeyframe && (
        <div className="w-80 border-l border-border bg-bg-surface overflow-auto flex-shrink-0">
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-text-primary">Keyframe Details</h3>
              <button onClick={() => setSelectedKeyframe(null)} className="text-text-muted hover:text-text-primary">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-muted block mb-1">Order Index</label>
                <p className="text-sm text-text-primary">{selectedKeyframe.order_index ?? '--'}</p>
              </div>
              <div>
                <label className="text-xs text-text-muted block mb-1">Prompt</label>
                <p className="text-sm text-text-primary whitespace-pre-wrap">{selectedKeyframe.prompt || 'None'}</p>
              </div>
              <div>
                <label className="text-xs text-text-muted block mb-1">Negative Prompt</label>
                <p className="text-sm text-text-secondary">{selectedKeyframe.negative_prompt || 'None'}</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-text-muted block mb-1">Model</label>
                  <p className="text-sm text-text-primary">{selectedKeyframe.model_id || 'Default'}</p>
                </div>
                <div>
                  <label className="text-xs text-text-muted block mb-1">Scheduler</label>
                  <p className="text-sm text-text-primary">{selectedKeyframe.scheduler || 'Default'}</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-text-muted block mb-1">Steps</label>
                  <p className="text-sm text-text-primary">{selectedKeyframe.steps ?? '--'}</p>
                </div>
                <div>
                  <label className="text-xs text-text-muted block mb-1">CFG</label>
                  <p className="text-sm text-text-primary">{selectedKeyframe.cfg_scale ?? '--'}</p>
                </div>
                <div>
                  <label className="text-xs text-text-muted block mb-1">Seed</label>
                  <p className="text-sm text-text-primary font-mono text-xs">{selectedKeyframe.seed ?? 'Random'}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-text-muted block mb-1">Width</label>
                  <p className="text-sm text-text-primary">{selectedKeyframe.width ?? '--'}px</p>
                </div>
                <div>
                  <label className="text-xs text-text-muted block mb-1">Height</label>
                  <p className="text-sm text-text-primary">{selectedKeyframe.height ?? '--'}px</p>
                </div>
              </div>
              <div>
                <label className="text-xs text-text-muted block mb-1">Storyboard ID</label>
                <p className="text-xs text-text-secondary font-mono truncate">{selectedKeyframe.storyboard_id}</p>
              </div>
              <div>
                <label className="text-xs text-text-muted block mb-1">Created</label>
                <p className="text-xs text-text-secondary">
                  {selectedKeyframe.created_at
                    ? new Date(selectedKeyframe.created_at).toLocaleString()
                    : '--'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
