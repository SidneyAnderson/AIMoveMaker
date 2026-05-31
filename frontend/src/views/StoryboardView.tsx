import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listKeyframes, createKeyframe, deleteKeyframe, updateKeyframe } from '@/api/storyboard'
import api from '@/api/client'
import { getProject, listMembers, updateProject } from '@/api/projects'
import { useProjectStore } from '@/stores/projectStore'
import { useAuthStore } from '@/stores/authStore'
import { useEffect, useState } from 'react'
import { ImagePlus, Wand2, Send, Plus, Trash2, X, Save, History, Search, Sliders, Layers } from 'lucide-react'
import CanvasEditor from '@/components/canvas/CanvasEditor'
import { getAssetDownloadUrl } from '@/api/assets'
import { createTemplate, listHistory, listTemplates, applyTemplate, createHistory } from '@/api/prompts'
import { toast } from 'sonner'

interface KeyframeFormData {
  prompt: string
  negative_prompt: string
  model_id: string
  steps: number
  cfg_scale: number
  width: number
  height: number
  // Advanced ControlNet / LoRA editors (#10)
  cn_enabled: boolean
  cn_type: string
  cn_strength: number
  cn_control_asset_id: string
  lora_stack: Array<{ lora_id: string; weight: number }>
}

const defaultForm: KeyframeFormData = {
  prompt: '',
  negative_prompt: '',
  model_id: '',
  steps: 30,
  cfg_scale: 7.5,
  width: 512,
  height: 512,
  cn_enabled: false,
  cn_type: 'canny',
  cn_strength: 1.0,
  cn_control_asset_id: '',
  lora_stack: [],
}

export default function StoryboardView() {
  const { projectId } = useParams<{ projectId: string }>()
  const queryClient = useQueryClient()
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject)
  const selectedKeyframeId = useProjectStore((s) => s.selectedKeyframeId)
  const setSelectedKeyframe = useProjectStore((s) => s.setSelectedKeyframe)

  const currentProjectState = useProjectStore((s) => s.currentProjectState)
  const currentUserProjectRole = useProjectStore((s) => s.currentUserProjectRole)

  const isCreative = currentUserProjectRole === 'creative'
  const isEngineer = currentUserProjectRole === 'engineer'
  const canEditStoryboard = isCreative && currentProjectState === 'creative_active'
  const canSubmitHandoff = isCreative && currentProjectState === 'creative_active'
  const isReadOnly = !canEditStoryboard

  // Derived lock states for banner (referenced in JSX)
  const isLockedForCreative = currentProjectState !== 'creative_active'
  const isLockedForEngineer = currentProjectState === 'eng_active' || currentProjectState === 'pending_return'

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<KeyframeFormData>({ ...defaultForm })
  const [showCanvas, setShowCanvas] = useState(false)
  // Prompt picker polish (search)
  const [templateSearch, setTemplateSearch] = useState('')
  const [historySearch, setHistorySearch] = useState('')

  const currentUserId = useAuthStore((s) => s.user?.id)

  useEffect(() => {
    if (projectId) {
      setCurrentProject(projectId)

      // Load project state + user's role for persona gating
      Promise.all([
        getProject(projectId),
        listMembers(projectId),
      ])
        .then(([proj, membersRes]) => {
          const members = membersRes.items || []
          const myMembership = members.find((m: any) => m.user_id === currentUserId)
          const myRole = myMembership?.role || (currentUserId ? 'viewer' : null)

          const setProjectContext = useProjectStore.getState().setProjectContext
          setProjectContext(proj.state, myRole)
        })
        .catch(() => {
          // Non-fatal
        })
    }
    return () => {
      setCurrentProject(null)
      useProjectStore.getState().clearProjectContext()
    }
  }, [projectId, currentUserId])

  const { data, isLoading } = useQuery({
    queryKey: ['keyframes', projectId],
    queryFn: () => listKeyframes(projectId!),
    enabled: !!projectId,
  })

  const { data: templatesData } = useQuery({
    queryKey: ['templates', projectId],
    queryFn: () => listTemplates(projectId),
    enabled: !!projectId,
  })

  const { data: historyData } = useQuery({
    queryKey: ['prompt-history', projectId],
    queryFn: () => listHistory(projectId),
    enabled: !!projectId,
  })

  // LoRA registry for advanced editor (#10)
  const { data: lorasData } = useQuery({
    queryKey: ['loras'],
    queryFn: async () => {
      const res = await api.get('/loras/')
      return res.data
    },
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

      // Advanced ControlNet / LoRA (#10)
      if (formData.cn_enabled) {
        payload.cn_enabled = true
        payload.cn_type = formData.cn_type
        payload.cn_strength = formData.cn_strength
        if (formData.cn_control_asset_id) payload.cn_control_asset_id = formData.cn_control_asset_id
      }
      if (formData.lora_stack.length > 0) {
        payload.lora_stack = formData.lora_stack
      }
      return createKeyframe(projectId!, payload)
    },
    onSuccess: (newKf: any) => {
      queryClient.invalidateQueries({ queryKey: ['keyframes', projectId] })
      setShowForm(false)
      setForm({ ...defaultForm })
      toast.success('Keyframe created')
      // Auto-save to prompt history (advanced)
      createHistory({
        prompt_text: form.prompt,
        negative_prompt: form.negative_prompt || undefined,
        model_id: form.model_id || undefined,
        params: { steps: form.steps, cfg_scale: form.cfg_scale, width: form.width, height: form.height },
        project_id: projectId,
      }).catch(() => {})
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
        {/* State / Permission Banner */}
        {(isLockedForCreative || isLockedForEngineer || !canEditStoryboard) && (
          <div className="bg-yellow-900/30 border-b border-yellow-700 px-4 py-2 text-xs text-yellow-300">
            {currentProjectState === 'pending_handoff' && 'Project is awaiting Engineer handoff acceptance. Storyboard is read-only.'}
            {currentProjectState === 'eng_active' && 'Project is in Engineering phase. Only the Engineer can modify the timeline.'}
            {currentProjectState === 'pending_return' && 'Engineer has requested return to Creative. Awaiting acceptance.'}
            {currentProjectState === 'completed' && 'This project is marked as completed.'}
            {!isCreative && !isEngineer && currentProjectState && 'You have viewer access to this project.'}
          </div>
        )}

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
              disabled={!canEditStoryboard}
              className="flex items-center gap-1 px-3 py-1.5 bg-accent text-accent-fg rounded-btn text-xs hover:bg-accent-hover disabled:opacity-50"
            >
              <Plus className="w-3 h-3" /> Add Keyframe
            </button>
            <button
              disabled={!canEditStoryboard}
              className="flex items-center gap-1 px-3 py-1.5 bg-accent text-accent-fg rounded-btn text-xs hover:bg-accent-hover disabled:opacity-50"
            >
              <Wand2 className="w-3 h-3" /> Generate All
            </button>
            <button
              disabled={!canSubmitHandoff}
              className="flex items-center gap-1 px-3 py-1.5 bg-accent text-accent-fg rounded-btn text-xs hover:bg-accent-hover disabled:opacity-50"
            >
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

              {/* === Advanced ControlNet / LoRA Editors (#10) === */}
              <div className="col-span-2 border border-border rounded p-3 bg-bg-base space-y-3">
                {/* LoRA Stack */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs text-text-secondary flex items-center gap-1"><Layers className="w-3 h-3" /> LoRA Stack</label>
                    <button
                      type="button"
                      onClick={() => {
                        const firstLora = lorasData?.items?.[0]
                        if (firstLora) {
                          setForm({
                            ...form,
                            lora_stack: [...form.lora_stack, { lora_id: firstLora.id, weight: 0.8 }]
                          })
                        } else {
                          // Fallback manual entry
                          setForm({ ...form, lora_stack: [...form.lora_stack, { lora_id: '', weight: 0.8 }] })
                        }
                      }}
                      className="text-[10px] px-2 py-0.5 border border-border rounded hover:bg-bg-subtle"
                    >
                      + Add LoRA
                    </button>
                  </div>

                  {form.lora_stack.length > 0 && (
                    <div className="space-y-2">
                      {form.lora_stack.map((entry, idx) => (
                        <div key={idx} className="flex gap-2 items-center text-xs">
                          <select
                            value={entry.lora_id}
                            onChange={(e) => {
                              const newStack = [...form.lora_stack]
                              newStack[idx] = { ...newStack[idx], lora_id: e.target.value }
                              setForm({ ...form, lora_stack: newStack })
                            }}
                            className="flex-1 bg-bg-surface border border-border rounded px-2 py-1 text-xs"
                          >
                            <option value="">Select LoRA...</option>
                            {(lorasData?.items || []).map((l: any) => (
                              <option key={l.id} value={l.id}>{l.name || l.id} ({l.architecture || 'sd'})</option>
                            ))}
                          </select>
                          <input
                            type="range"
                            min="0"
                            max="2"
                            step="0.1"
                            value={entry.weight}
                            onChange={(e) => {
                              const newStack = [...form.lora_stack]
                              newStack[idx] = { ...newStack[idx], weight: parseFloat(e.target.value) }
                              setForm({ ...form, lora_stack: newStack })
                            }}
                            className="w-24"
                          />
                          <span className="w-8 font-mono text-center">{entry.weight.toFixed(1)}</span>
                          <button
                            type="button"
                            onClick={() => {
                              const newStack = form.lora_stack.filter((_, i) => i !== idx)
                              setForm({ ...form, lora_stack: newStack })
                            }}
                            className="text-red-400 hover:text-red-500"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  {form.lora_stack.length === 0 && (
                    <div className="text-[10px] text-text-muted">No LoRAs added (optional)</div>
                  )}
                </div>

                {/* ControlNet */}
                <div>
                  <label className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                    <input
                      type="checkbox"
                      checked={form.cn_enabled}
                      onChange={(e) => setForm({ ...form, cn_enabled: e.target.checked })}
                    />
                    <Sliders className="w-3 h-3" /> Use ControlNet
                  </label>

                  {form.cn_enabled && (
                    <div className="grid grid-cols-2 gap-2 mt-2 text-xs">
                      <div>
                        <label className="block text-[10px] text-text-muted mb-0.5">Type</label>
                        <select
                          value={form.cn_type}
                          onChange={(e) => setForm({ ...form, cn_type: e.target.value })}
                          className="w-full bg-bg-surface border border-border rounded px-2 py-1"
                        >
                          <option value="canny">Canny (edges)</option>
                          <option value="depth">Depth</option>
                          <option value="pose">OpenPose</option>
                          <option value="reference">Reference (IP-Adapter)</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[10px] text-text-muted mb-0.5">Strength</label>
                        <div className="flex items-center gap-2">
                          <input
                            type="range"
                            min="0"
                            max="2"
                            step="0.1"
                            value={form.cn_strength}
                            onChange={(e) => setForm({ ...form, cn_strength: parseFloat(e.target.value) })}
                            className="flex-1"
                          />
                          <span className="w-8 font-mono text-center">{form.cn_strength.toFixed(1)}</span>
                        </div>
                      </div>
                      <div className="col-span-2">
                        <label className="block text-[10px] text-text-muted mb-0.5">Control Image Asset ID (optional)</label>
                        <input
                          value={form.cn_control_asset_id}
                          onChange={(e) => setForm({ ...form, cn_control_asset_id: e.target.value })}
                          placeholder="Asset ID or upload via Canvas first"
                          className="w-full bg-bg-surface border border-border rounded px-2 py-1 text-xs"
                        />
                      </div>
                    </div>
                  )}
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
                  <div className="aspect-square bg-bg-subtle relative overflow-hidden">
                    {kf.selected_asset_id || kf.thumbnail_asset_id ? (
                      <img
                        src={getAssetDownloadUrl(projectId!, kf.selected_asset_id || kf.thumbnail_asset_id)}
                        alt=""
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          const el = e.currentTarget as HTMLImageElement
                          el.style.display = 'none'
                          // Show fallback icon
                          const fallback = el.parentElement?.querySelector('.fallback-icon') as HTMLElement
                          if (fallback) fallback.style.display = 'flex'
                        }}
                      />
                    ) : null}
                    <div className="fallback-icon absolute inset-0 hidden items-center justify-center bg-bg-subtle">
                      <ImagePlus className="w-6 h-6 text-text-muted opacity-30" />
                    </div>
                    {!(kf.selected_asset_id || kf.thumbnail_asset_id) && (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <ImagePlus className="w-6 h-6 text-text-muted opacity-30" />
                      </div>
                    )}

                    {/* Advanced Candidate Carousel (when variation_count > 1 or candidates exist) */}
                    {Array.isArray(kf.candidate_asset_ids) && kf.candidate_asset_ids.length > 1 && (
                      <div className="absolute bottom-0 left-0 right-0 bg-black/60 p-1 flex gap-1 overflow-x-auto scrollbar-thin">
                        {kf.candidate_asset_ids.slice(0, 6).map((aid: string) => {
                          const isSelected = aid === kf.selected_asset_id;
                          return (
                            <img
                              key={aid}
                              src={getAssetDownloadUrl(projectId!, aid)}
                              alt=""
                              className={`h-8 w-8 object-cover rounded border flex-shrink-0 cursor-pointer ${isSelected ? 'border-accent ring-1 ring-accent' : 'border-white/40 hover:border-white'}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                updateKeyframe(projectId!, kf.id, { selected_asset_id: aid })
                                  .then(() => {
                                    queryClient.invalidateQueries({ queryKey: ['keyframes', projectId] });
                                    toast.success('Selected candidate');
                                  })
                                  .catch(() => toast.error('Failed to select asset'));
                              }}
                            />
                          );
                        })}
                        {kf.candidate_asset_ids.length > 6 && (
                          <span className="text-[10px] text-white/70 self-center px-1">+{kf.candidate_asset_ids.length - 6}</span>
                        )}
                      </div>
                    )}

                    <span className="absolute top-1 left-1 text-[10px] bg-bg-base/80 px-1 rounded">
                      {String((kf.order_index ?? idx) + 1).padStart(2, '0')}
                    </span>
                    <span className={`absolute top-1 right-1 w-2 h-2 rounded-full ${
                      kf.thumbnail_asset_id ? 'bg-success' : 'bg-text-muted'
                    }`} />
                    {/* Action buttons on hover */}
                    <div className="absolute bottom-1 right-1 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedKeyframe(kf.id)
                          setShowCanvas(true)
                        }}
                        className="p-1 bg-bg-base/80 rounded hover:bg-accent/30"
                        title="Edit in Canvas"
                      >
                        <ImagePlus className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          if (confirm('Delete this keyframe?')) {
                            deleteMutation.mutate(kf.id)
                          }
                        }}
                        className="p-1 bg-bg-base/80 rounded hover:bg-error/20"
                        title="Delete"
                      >
                        <Trash2 className="w-3 h-3 text-error" />
                      </button>
                    </div>
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

              {/* Global Negative Prompt + Scope Toggle (PRD 4.4.3) */}
              <div className="mt-3 p-2 bg-bg-base rounded border border-border">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-text-muted">Negative Scope</span>
                  <select
                    value={selectedKeyframe.neg_prompt_scope || 'global'}
                    onChange={async (e) => {
                      const newScope = e.target.value
                      try {
                        await updateKeyframe(projectId!, selectedKeyframe.id, { neg_prompt_scope: newScope })
                        queryClient.invalidateQueries({ queryKey: ['keyframes', projectId] })
                        toast.success('Scope updated')
                      } catch {
                        toast.error('Failed to update scope')
                      }
                    }}
                    className="text-xs bg-bg-surface border border-border rounded px-1 py-0.5"
                  >
                    <option value="global">Global</option>
                    <option value="keyframe">This keyframe only</option>
                  </select>
                </div>

                <div className="text-[10px] text-text-muted mb-1">Project Global Negative</div>
                <textarea
                  defaultValue={'' /* will be loaded from project */}
                  placeholder="Enter project-wide negative prompt..."
                  className="w-full text-xs bg-bg-surface border border-border rounded p-1 resize-y h-12"
                  onBlur={async (e) => {
                    try {
                      await updateProject(projectId!, { global_negative_prompt: e.target.value })
                      toast.success('Global negative updated')
                    } catch {
                      toast.error('Failed to save global negative')
                    }
                  }}
                />
                <div className="text-[9px] text-text-muted mt-0.5">Used when scope = Global</div>
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

              {/* Deeper ControlNet / LoRA polish (advanced low item) */}
              {selectedKeyframe.cn_enabled && (
                <div className="mt-2 text-xs border border-border rounded p-2 bg-bg-base">
                  <div className="text-text-muted">ControlNet</div>
                  <div className="font-mono text-[10px] text-text-primary">
                    {selectedKeyframe.cn_type} · strength {selectedKeyframe.cn_strength ?? 1.0}
                  </div>
                  <div className="text-[10px] text-text-muted mt-0.5">LoRA stack: {(selectedKeyframe.lora_stack || []).length} items</div>
                </div>
              )}
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

              <button
                onClick={() => setShowCanvas(true)}
                className="mt-4 w-full flex items-center justify-center gap-2 px-3 py-2 bg-accent text-accent-fg rounded-btn text-sm hover:bg-accent-hover"
                disabled={!selectedKeyframe.thumbnail_asset_id && !selectedKeyframe.selected_asset_id}
              >
                <ImagePlus className="w-4 h-4" /> Edit in Canvas
              </button>

              {/* Advanced Candidate Carousel / Picker in detail panel */}
              {Array.isArray(selectedKeyframe.candidate_asset_ids) && selectedKeyframe.candidate_asset_ids.length > 1 && (
                <div className="mt-4">
                  <div className="text-xs text-text-muted mb-1.5">Candidates ({selectedKeyframe.candidate_asset_ids.length})</div>
                  <div className="flex gap-2 overflow-x-auto pb-1">
                    {selectedKeyframe.candidate_asset_ids.map((aid: string) => {
                      const isSel = aid === selectedKeyframe.selected_asset_id;
                      return (
                        <div
                          key={aid}
                          onClick={async () => {
                            try {
                              await updateKeyframe(projectId!, selectedKeyframe.id, { selected_asset_id: aid });
                              queryClient.invalidateQueries({ queryKey: ['keyframes', projectId] });
                              toast.success('Selected candidate asset');
                            } catch {
                              toast.error('Failed to select');
                            }
                          }}
                          className={`cursor-pointer rounded border flex-shrink-0 ${isSel ? 'border-accent ring-1 ring-accent' : 'border-border hover:border-border-strong'}`}
                        >
                          <img
                            src={getAssetDownloadUrl(projectId!, aid)}
                            alt=""
                            className="w-16 h-16 object-cover rounded"
                          />
                        </div>
                      );
                    })}
                  </div>
                  <div className="text-[10px] text-text-muted mt-0.5">Click a candidate to set as selected</div>
                </div>
              )}

              {/* Advanced Prompt Templates integration */}
              <button
                onClick={async () => {
                  const title = prompt('Template title?', selectedKeyframe.prompt?.slice(0, 50) || 'New Template')
                  if (!title) return
                  try {
                    await createTemplate({
                      title,
                      positive_prompt: selectedKeyframe.prompt,
                      negative_prompt: selectedKeyframe.negative_prompt,
                      model_id: selectedKeyframe.model_id,
                      params: {
                        steps: selectedKeyframe.steps,
                        cfg_scale: selectedKeyframe.cfg_scale,
                        width: selectedKeyframe.width,
                        height: selectedKeyframe.height,
                      },
                      scope: 'project',
                      project_id: projectId,
                    })
                    toast.success('Saved as project template')
                  } catch (e) {
                    toast.error('Failed to save template (backend may need the route)')
                  }
                }}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 border border-border rounded-btn text-sm hover:bg-bg-subtle"
              >
                <Save className="w-4 h-4" /> Save as Template
              </button>

              {/* Advanced Prompt Templates picker (polished: search + scope + more items) */}
              {templatesData?.items?.length > 0 && (
                <div className="mt-3">
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-xs text-text-muted">Templates</div>
                    <div className="relative">
                      <Search className="w-3 h-3 absolute left-1.5 top-1 text-text-muted" />
                      <input
                        value={templateSearch}
                        onChange={(e) => setTemplateSearch(e.target.value)}
                        placeholder="Search..."
                        className="text-[10px] pl-5 pr-1 py-0.5 bg-bg-base border border-border rounded w-24"
                      />
                    </div>
                  </div>
                  <div className="space-y-1 max-h-24 overflow-auto text-xs">
                    {templatesData.items
                      .filter((t: any) => !templateSearch || t.title?.toLowerCase().includes(templateSearch.toLowerCase()) || t.positive_prompt?.toLowerCase().includes(templateSearch.toLowerCase()))
                      .slice(0, 8)
                      .map((t: any) => (
                        <button
                          key={t.id}
                          onClick={async () => {
                            try {
                              const data = await applyTemplate(t.id)
                              if (selectedKeyframe) {
                                await updateKeyframe(projectId!, selectedKeyframe.id, {
                                  prompt: data.positive_prompt,
                                  negative_prompt: data.negative_prompt,
                                  model_id: data.model_id,
                                  ...(data.params || {}),
                                })
                                toast.success('Template applied')
                              }
                            } catch (e) {
                              toast.error('Failed to apply template')
                            }
                          }}
                          className="block w-full text-left text-xs px-2 py-1 bg-bg-base border border-border rounded hover:bg-bg-subtle truncate flex items-center gap-1"
                        >
                          <span className="truncate flex-1">{t.title}</span>
                          <span className="text-[9px] px-1 rounded bg-bg-subtle text-text-muted flex-shrink-0">{t.scope}</span>
                        </button>
                      ))}
                    {templatesData.items.filter((t: any) => !templateSearch || t.title?.toLowerCase().includes(templateSearch.toLowerCase())).length === 0 && (
                      <div className="text-[10px] text-text-muted px-2">No matches</div>
                    )}
                  </div>
                </div>
              )}

              {/* Advanced Prompt History panel (polished) */}
              {historyData?.items?.length > 0 && (
                <div className="mt-3">
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-xs text-text-muted">Recent History</div>
                    <div className="relative">
                      <Search className="w-3 h-3 absolute left-1.5 top-1 text-text-muted" />
                      <input
                        value={historySearch}
                        onChange={(e) => setHistorySearch(e.target.value)}
                        placeholder="Search..."
                        className="text-[10px] pl-5 pr-1 py-0.5 bg-bg-base border border-border rounded w-24"
                      />
                    </div>
                  </div>
                  <div className="space-y-0.5 max-h-24 overflow-auto text-xs">
                    {historyData.items
                      .filter((h: any) => !historySearch || h.prompt_text?.toLowerCase().includes(historySearch.toLowerCase()))
                      .slice(0, 8)
                      .map((h: any) => (
                        <button
                          key={h.id}
                          onClick={async () => {
                            if (selectedKeyframe) {
                              await updateKeyframe(projectId!, selectedKeyframe.id, {
                                prompt: h.prompt_text,
                                negative_prompt: h.negative_prompt,
                              })
                              toast.success('History applied')
                            }
                          }}
                          className="block w-full text-left px-2 py-0.5 hover:bg-bg-subtle truncate text-text-secondary"
                          title={h.prompt_text}
                        >
                          {h.prompt_text?.slice(0, 55)}{h.prompt_text?.length > 55 ? '...' : ''}
                          <span className="text-[9px] text-text-muted ml-1">({new Date(h.used_at || h.created_at).toLocaleDateString()})</span>
                        </button>
                      ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Canvas Editor */}
      {showCanvas && selectedKeyframe && projectId && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="w-full max-w-[1200px] bg-bg-elevated border border-border rounded-card shadow-2xl overflow-hidden">
            <CanvasEditor
              projectId={projectId}
              keyframeId={selectedKeyframe.id}
              assetId={selectedKeyframe.selected_asset_id || selectedKeyframe.thumbnail_asset_id || null}
              initialPrompt={selectedKeyframe.prompt || ''}
              onClose={() => {
                setShowCanvas(false)
                // Always refresh after closing Canvas (new assets or transforms may have been created)
                queryClient.invalidateQueries({ queryKey: ['keyframes', projectId] })
              }}
              onAssetUpdated={async (newAssetId) => {
                try {
                  await updateKeyframe(projectId!, selectedKeyframe.id, { selected_asset_id: newAssetId })
                  queryClient.invalidateQueries({ queryKey: ['keyframes', projectId] })
                  toast.success('Updated selected asset for keyframe')
                } catch (e) {
                  console.error(e)
                }
              }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
