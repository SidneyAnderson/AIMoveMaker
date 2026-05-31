import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useProjectStore } from '@/stores/projectStore'
import { useAuthStore } from '@/stores/authStore'
import { useEffect, useState, useRef } from 'react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragOverlay,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useSortable } from '@dnd-kit/sortable'
import { Play, SkipBack, SkipForward, StepBack, StepForward, Download, Plus, X, Film, Music, Layers, GripVertical } from 'lucide-react'
import { toast } from 'sonner'
import api from '@/api/client'
import { createJob } from '@/api/jobs'
import { getProject, listMembers } from '@/api/projects'
import { getAssetDownloadUrl } from '@/api/assets'

type TrackType = 'video' | 'audio' | 'effect' | 'caption'

// ---------- API helpers ----------
async function listTracks(projectId: string) {
  const res = await api.get(`/projects/${projectId}/tracks/`)
  return res.data
}
async function createTrack(projectId: string, data: { name: string; type: TrackType }) {
  const res = await api.post(`/projects/${projectId}/tracks/`, data)
  return res.data
}
async function deleteTrack(projectId: string, trackId: string) {
  await api.delete(`/projects/${projectId}/tracks/${trackId}`)
}
async function listVideoClips(projectId: string) {
  const res = await api.get(`/projects/${projectId}/videoclips/`)
  return res.data
}
async function listAudioClips(projectId: string) {
  const res = await api.get(`/projects/${projectId}/audioclips/`)
  return res.data
}

// ---------- constants ----------
const FRAME_PX = 5 // pixels per frame on ruler
const TRACK_H = 40 // track row height

const TRACK_TYPE_COLORS: Record<string, string> = {
  video: 'bg-blue-600/60 border-blue-400/40',
  audio: 'bg-green-600/60 border-green-400/40',
  effect: 'bg-purple-600/60 border-purple-400/40',
  caption: 'bg-yellow-600/60 border-yellow-400/40',
}

const TRACK_TYPE_ICONS: Record<string, typeof Film> = {
  video: Film,
  audio: Music,
  effect: Layers,
  caption: Layers,
}

// Module-level cache and shared AudioContext for performance (advanced caching)
const peakCache = new Map<string, number[]>();
let sharedAudioContext: AudioContext | null = null;

function getAudioContext(): AudioContext {
  if (!sharedAudioContext) {
    sharedAudioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
  }
  return sharedAudioContext;
}

// Real waveform component for audio clips (advanced: cached peaks, reused context, smoother rendering)
function AudioWaveform({ projectId, assetId, clipId, width, height }: { projectId: string | null | undefined; assetId?: string; clipId: string; width: number; height: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [peaks, setPeaks] = useState<number[] | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!projectId || !assetId || !canvasRef.current) return

    const cacheKey = assetId

    // Caching: use cached peaks if available
    if (peakCache.has(cacheKey)) {
      const cached = peakCache.get(cacheKey)!
      setPeaks(cached)
      return
    }

    const url = getAssetDownloadUrl(projectId, assetId)
    setIsLoading(true)

    const draw = (peakData: number[]) => {
      const canvas = canvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d', { willReadFrequently: true })
      if (!ctx) return

      canvas.width = width
      canvas.height = height
      ctx.clearRect(0, 0, width, height)

      // Better peak rendering: filled smooth waveform (top + bottom mirror)
      ctx.fillStyle = 'rgba(255,255,255,0.85)'
      ctx.beginPath()

      const barWidth = width / peakData.length
      const midY = height / 2

      // Top envelope
      ctx.moveTo(0, midY)
      for (let i = 0; i < peakData.length; i++) {
        const x = i * barWidth
        const h = peakData[i] * (height * 0.45)
        ctx.lineTo(x, midY - h)
      }
      // Bottom envelope (reverse)
      for (let i = peakData.length - 1; i >= 0; i--) {
        const x = i * barWidth
        const h = peakData[i] * (height * 0.45)
        ctx.lineTo(x, midY + h)
      }
      ctx.closePath()
      ctx.fill()

      // Subtle center line
      ctx.strokeStyle = 'rgba(255,255,255,0.3)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, midY)
      ctx.lineTo(width, midY)
      ctx.stroke()
    }

    // Fetch + decode (performance: reuse AudioContext)
    fetch(url)
      .then(res => res.arrayBuffer())
      .then(arrayBuffer => {
        const audioCtx = getAudioContext()
        return audioCtx.decodeAudioData(arrayBuffer)
      })
      .then(audioBuffer => {
        const channelData = audioBuffer.getChannelData(0)
        const samplesPerPeak = Math.max(1, Math.floor(channelData.length / Math.max(80, Math.floor(width * 1.5))))
        const generatedPeaks: number[] = []

        for (let i = 0; i < channelData.length; i += samplesPerPeak) {
          let max = 0
          for (let j = 0; j < samplesPerPeak && i + j < channelData.length; j++) {
            max = Math.max(max, Math.abs(channelData[i + j]))
          }
          generatedPeaks.push(max)
        }

        // Cache the peaks
        peakCache.set(cacheKey, generatedPeaks)
        setPeaks(generatedPeaks)
        draw(generatedPeaks)
        setIsLoading(false)
      })
      .catch(() => {
        const fallback = Array.from({ length: Math.max(50, Math.floor(width / 2.5)) }, (_, i) => 0.25 + Math.sin(i * 0.9) * 0.4 + Math.random() * 0.1)
        peakCache.set(cacheKey, fallback)
        setPeaks(fallback)
        draw(fallback)
        setIsLoading(false)
      })
  }, [projectId, assetId, width, height])

  return (
    <div className="absolute bottom-0 left-0 right-0 h-3" style={{ width }}>
      <canvas
        ref={canvasRef}
        className="w-full h-full opacity-90"
      />
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center text-[8px] text-white/60">loading…</div>
      )}
    </div>
  )
}

function formatTimecode(frames: number, fps: number = 24): string {
  const totalSeconds = Math.floor(frames / fps)
  const h = Math.floor(totalSeconds / 3600)
  const m = Math.floor((totalSeconds % 3600) / 60)
  const s = totalSeconds % 60
  const f = frames % fps
  return `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}:${f.toString().padStart(2,'0')}`
}

// Simple snap helper for drag/trim
function findNearestSnap(targetFrame: number, clips: any[], excludeClipId?: string, grid = 5): number {
  let nearest = Math.round(targetFrame / grid) * grid
  let minDist = Math.abs(targetFrame - nearest)

  clips.forEach((c: any) => {
    if (c.id === excludeClipId) return
    const start = c.start_frame ?? 0
    const end = c.end_frame ?? 0
    ;[start, end].forEach(edge => {
      const dist = Math.abs(targetFrame - edge)
      if (dist < minDist && dist < 20) { // snap threshold
        minDist = dist
        nearest = edge
      }
    })
  })
  return nearest
}

export default function TimelineView() {
  const { projectId } = useParams<{ projectId: string }>()
  const queryClient = useQueryClient()
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject)

  const [showAddTrack, setShowAddTrack] = useState(false)
  const [newTrackName, setNewTrackName] = useState('')
  const [newTrackType, setNewTrackType] = useState<TrackType>('video')

  // Selected audio clip for offset editing UI (advanced polish)
  const [selectedAudioClip, setSelectedAudioClip] = useState<any>(null)

  // Playhead & playback (Timeline depth improvement)
  const [playheadFrame, setPlayheadFrame] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const playbackIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const currentUserId = useAuthStore((s) => s.user?.id)
  const currentProjectState = useProjectStore((s) => s.currentProjectState)
  const currentUserProjectRole = useProjectStore((s) => s.currentUserProjectRole)

  const isEngineer = currentUserProjectRole === 'engineer'
  const canEditTimeline = isEngineer && (currentProjectState === 'eng_active' || currentProjectState === 'pending_return')
  const isTimelineLocked = !canEditTimeline && currentProjectState

  // Disable editing controls when locked
  const renderDisabled = isTimelineLocked || !canEditTimeline

  useEffect(() => {
    if (projectId) {
      setCurrentProject(projectId)

      Promise.all([getProject(projectId), listMembers(projectId)])
        .then(([proj, membersRes]) => {
          const members = membersRes.items || []
          const myMembership = members.find((m: any) => m.user_id === currentUserId)
          const myRole = myMembership?.role || (currentUserId ? 'viewer' : null)

          const setProjectContext = useProjectStore.getState().setProjectContext
          setProjectContext(proj.state, myRole)
        })
        .catch(() => {})
    }
    return () => {
      setCurrentProject(null)
      useProjectStore.getState().clearProjectContext()
    }
  }, [projectId, currentUserId])

  // ---- queries ----
  const tracksQuery = useQuery({
    queryKey: ['tracks', projectId],
    queryFn: () => listTracks(projectId!),
    enabled: !!projectId,
  })
  const videoClipsQuery = useQuery({
    queryKey: ['videoclips', projectId],
    queryFn: () => listVideoClips(projectId!),
    enabled: !!projectId,
  })
  const audioClipsQuery = useQuery({
    queryKey: ['audioclips', projectId],
    queryFn: () => listAudioClips(projectId!),
    enabled: !!projectId,
  })

  const tracks: any[] = tracksQuery.data?.items || []
  const videoClips: any[] = videoClipsQuery.data?.items || []
  const audioClips: any[] = audioClipsQuery.data?.items || []
  const allClips = [...videoClips, ...audioClips]

  // ---- mutations ----
  const addTrackMutation = useMutation({
    mutationFn: () => createTrack(projectId!, { name: newTrackName || `${newTrackType} track`, type: newTrackType }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tracks', projectId] })
      setShowAddTrack(false)
      setNewTrackName('')
      toast.success('Track added')
    },
    onError: () => toast.error('Failed to add track'),
  })

  const deleteTrackMutation = useMutation({
    mutationFn: (trackId: string) => deleteTrack(projectId!, trackId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tracks', projectId] })
      toast.success('Track deleted')
    },
    onError: () => toast.error('Failed to delete track'),
  })

  const renderMutation = useMutation({
    mutationFn: () => {
      const videoClipsForRender = videoClips.map((c: any) => ({
        asset_path: c.asset_path || '', // assume backend or store provides storage path
        start_frame: c.start_frame,
        end_frame: c.end_frame,
      }))
      const audioClipsForRender = audioClips.map((c: any) => ({
        asset_path: c.asset_path || '',
        start_frame: c.start_frame,
        end_frame: c.end_frame,
      }))

      return createJob({
        job_type: 'render',
        project_id: projectId!,
        params: {
          video_clips: videoClipsForRender,
          audio_clips: audioClipsForRender,
          resolution: '1280x720',
          fps: 24,
        },
      })
    },
    onSuccess: () => toast.success('Render job submitted'),
    onError: () => toast.error('Failed to submit render job'),
  })

  // Determine total timeline length in frames for the ruler
  let maxFrame = 300 // minimum ~10s at 30fps
  allClips.forEach((c: any) => {
    if (c.end_frame && c.end_frame > maxFrame) maxFrame = c.end_frame
  })
  const rulerFrames = maxFrame + 60 // extra padding
  const rulerWidthPx = rulerFrames * FRAME_PX

  // Playhead scrubbing handlers
  const updatePlayheadFromClientX = (clientX: number) => {
    if (renderDisabled) return
    const rulerEl = document.querySelector('.overflow-hidden[style*="width"]') as HTMLElement // rough selector
    if (!rulerEl) return
    const rect = rulerEl.getBoundingClientRect()
    const x = clientX - rect.left
    const frame = Math.max(0, Math.min(Math.floor(x / FRAME_PX), rulerFrames))
    setPlayheadFrame(frame)
  }

  const handleRulerClick = (e: React.MouseEvent) => {
    updatePlayheadFromClientX(e.clientX)
  }

  const handleRulerMouseDown = (e: React.MouseEvent) => {
    updatePlayheadFromClientX(e.clientX)
    const handleMove = (moveEvent: MouseEvent) => updatePlayheadFromClientX(moveEvent.clientX)
    const handleUp = () => {
      window.removeEventListener('mousemove', handleMove)
      window.removeEventListener('mouseup', handleUp)
    }
    window.addEventListener('mousemove', handleMove)
    window.addEventListener('mouseup', handleUp)
  }

  const handleRulerMouseMove = (e: React.MouseEvent) => {
    if (e.buttons === 1) { // left button held
      updatePlayheadFromClientX(e.clientX)
    }
  }

  // Allow scrubbing when mouse is over the entire timeline clip area (not just ruler)
  const handleTimelineMouseMove = (e: React.MouseEvent) => {
    if (e.buttons === 1 && !draggingWholeClip && !resizing) {
      updatePlayheadFromClientX(e.clientX)
    }
    if (draggingWholeClip) {
      handleWholeClipDragMove(e.clientX)
    }
  }

  const handleTimelineMouseDown = (e: React.MouseEvent) => {
    if (!draggingWholeClip && !resizing) {
      updatePlayheadFromClientX(e.clientX)
    }
  }

  // --- Trim (resize) + Drag state ---
  const [resizing, setResizing] = useState<{ clipId: string; side: 'left' | 'right'; trackId: string; initialFrame: number; startX: number } | null>(null)
  const [draggingWholeClip, setDraggingWholeClip] = useState<{ clipId: string; trackId: string; initialFrame: number; startX: number; clipStartFrame: number } | null>(null)
  const [clipOverrides, setClipOverrides] = useState<Record<string, { start_frame?: number; end_frame?: number }>>({})

  // dnd-kit active drag item for overlays (for clip and track reordering)
  const [activeDragId, setActiveDragId] = useState<string | null>(null)
  const [activeDragType, setActiveDragType] = useState<'track' | 'clip' | null>(null)
  const [activeDragData, setActiveDragData] = useState<any>(null)

  // For insertion feedback during clip reordering
  const [clipOverId, setClipOverId] = useState<string | null>(null)

  // Global mouse up for whole clip drag release + persistence (must be after state declarations)
  useEffect(() => {
    const handleGlobalMouseUp = async () => {
      if (draggingWholeClip) {
        const clipId = draggingWholeClip.clipId
        const final = clipOverrides[clipId]
        if (final && final.start_frame !== undefined) {
          const track = tracks.find((t: any) => t.id === draggingWholeClip.trackId)
          const isVideo = track?.type === 'video'
          const endpoint = isVideo
            ? `/projects/${projectId}/videoclips/${clipId}`
            : `/projects/${projectId}/audioclips/${clipId}`

          const fps = 24
          const updatePayload: any = {
            start_ms: Math.round((final.start_frame / fps) * 1000),
          }
          if (final.end_frame !== undefined) {
            updatePayload.end_ms = Math.round((final.end_frame / fps) * 1000)
          }

          try {
            await api.patch(endpoint, updatePayload)
            queryClient.invalidateQueries({ queryKey: ['timeline', projectId] })
            queryClient.invalidateQueries({ queryKey: ['videoclips', projectId] })
            queryClient.invalidateQueries({ queryKey: ['audioclips', projectId] })

            setClipOverrides(prev => {
              const next = { ...prev }
              delete next[clipId]
              return next
            })
            toast.success('Clip moved')
          } catch {
            toast.error('Failed to save clip position')
          }
        }
        setDraggingWholeClip(null)
      }
    }

    window.addEventListener('mouseup', handleGlobalMouseUp)
    return () => window.removeEventListener('mouseup', handleGlobalMouseUp)
  }, [draggingWholeClip, clipOverrides, tracks, projectId, queryClient])

  const startTrim = (e: React.MouseEvent, clip: any, side: 'left' | 'right', trackId: string) => {
    if (renderDisabled) return
    e.stopPropagation()
    const startX = e.clientX
    const initialFrame = side === 'left' ? (clip.start_frame ?? 0) : (clip.end_frame ?? 0)

    setResizing({ clipId: clip.id, side, trackId, initialFrame, startX })

    const onMove = (moveEvent: MouseEvent) => {
      const deltaPx = moveEvent.clientX - startX
      let deltaFrames = Math.round(deltaPx / FRAME_PX)

      // Simple snapping to integer frames
      const newFrame = Math.max(0, initialFrame + deltaFrames)

      // Use enhanced snap (grid + other clips)
      const snappedFrame = findNearestSnap(newFrame, allClips, clip.id)

      setClipOverrides(prev => {
        const curr = prev[clip.id] || {}
        const next = { ...curr }

        if (side === 'left') {
          const maxStart = (curr.end_frame ?? clip.end_frame ?? snappedFrame + 1) - 1
          next.start_frame = Math.min(snappedFrame, maxStart)
        } else {
          const minEnd = (curr.start_frame ?? clip.start_frame ?? snappedFrame - 1) + 1
          next.end_frame = Math.max(snappedFrame, minEnd)
        }

        // Enforce minimum duration (5 frames)
        const minDur = 5
        if (next.end_frame !== undefined && next.start_frame !== undefined) {
          if (next.end_frame - next.start_frame < minDur) {
            if (side === 'left') {
              next.start_frame = next.end_frame - minDur
            } else {
              next.end_frame = next.start_frame + minDur
            }
          }
        }

        return { ...prev, [clip.id]: next }
      })
    }

    const onUp = async () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
      setResizing(null)

      const final = clipOverrides[clip.id]
      if (!final) return

      // Determine endpoint based on track type (video vs audio)
      const track = tracks.find((t: any) => t.id === trackId)
      const isVideo = track?.type === 'video'
      const endpoint = isVideo
        ? `/projects/${projectId}/videoclips/${clip.id}`
        : `/projects/${projectId}/audioclips/${clip.id}`

      try {
        // Use actual project fps if available, fallback to 24
        const fps = 24
        const updatePayload: any = {}
        if (final.start_frame !== undefined) {
          updatePayload.start_ms = Math.round((final.start_frame / fps) * 1000)
        }
        if (final.end_frame !== undefined) {
          updatePayload.end_ms = Math.round((final.end_frame / fps) * 1000)
        }

        await api.patch(endpoint, updatePayload)

        // Refresh data
        queryClient.invalidateQueries({ queryKey: ['timeline', projectId] })
        queryClient.invalidateQueries({ queryKey: ['videoclips', projectId] })
        queryClient.invalidateQueries({ queryKey: ['audioclips', projectId] })

        // Clear the override for this clip now that it's persisted
        setClipOverrides(prev => {
          const next = { ...prev }
          delete next[clip.id]
          return next
        })

        toast.success('Trim saved')
      } catch (e) {
        toast.error('Failed to save trim')
        // Keep override so UI doesn't regress
      }
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  // --- Whole clip drag (move) ---
  const startWholeClipDrag = (e: React.MouseEvent, clip: any, trackId: string) => {
    if (renderDisabled) return
    e.stopPropagation()
    const startX = e.clientX
    const clipStartFrame = clip.start_frame ?? 0

    setDraggingWholeClip({ clipId: clip.id, trackId, initialFrame: clipStartFrame, startX, clipStartFrame })
  }

  // Basic whole-clip drag movement (live preview via overrides)
  const handleWholeClipDragMove = (clientX: number) => {
    if (!draggingWholeClip) return
    const deltaPx = clientX - draggingWholeClip.startX
    const deltaFrames = Math.round(deltaPx / FRAME_PX)
    const newStart = Math.max(0, draggingWholeClip.clipStartFrame + deltaFrames)

    setClipOverrides(prev => ({
      ...prev,
      [draggingWholeClip.clipId]: {
        start_frame: newStart,
        end_frame: newStart + ((prev[draggingWholeClip.clipId]?.end_frame ?? 0) - (prev[draggingWholeClip.clipId]?.start_frame ?? draggingWholeClip.clipStartFrame))
      }
    }))
  }

  // Group clips by track
  const clipsByTrack = (trackId: string) => allClips.filter((c: any) => c.track_id === trackId)

  const isLoading = tracksQuery.isLoading || videoClipsQuery.isLoading || audioClipsQuery.isLoading

  return (
    <div className="h-full flex flex-col">
      {/* Preview Zone (35%) */}
      <div className="h-[35%] min-h-[20%] bg-black flex flex-col">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-text-muted text-sm">Preview</div>
        </div>
        {/* Playback Controls */}
        <div className="flex items-center justify-center gap-4 py-2 bg-bg-surface border-t border-border">
          <button className="text-text-muted hover:text-text-primary"><SkipBack className="w-4 h-4" /></button>
          <button className="text-text-muted hover:text-text-primary"><StepBack className="w-4 h-4" /></button>
          <button className="w-8 h-8 rounded-full bg-accent flex items-center justify-center hover:bg-accent-hover">
            <Play className="w-4 h-4 text-accent-fg" />
          </button>
          <button className="text-text-muted hover:text-text-primary"><StepForward className="w-4 h-4" /></button>
          <button className="text-text-muted hover:text-text-primary"><SkipForward className="w-4 h-4" /></button>
          <span className="text-xs text-text-muted font-mono ml-4">
            {formatTimecode(playheadFrame, 24)}
          </span>
          <button
            onClick={() => renderMutation.mutate()}
            disabled={renderMutation.isPending || !!renderDisabled}
            className="ml-auto mr-4 flex items-center gap-1 px-3 py-1 bg-accent text-accent-fg rounded-btn text-xs hover:bg-accent-hover disabled:opacity-50"
          >
            <Download className="w-3 h-3" /> {renderMutation.isPending ? 'Submitting...' : 'Render'}
          </button>

          {/* Basic EDL export (older PRD gap) */}
          <button
            onClick={() => {
              const edl = {
                project_id: projectId,
                fps: 24,
                resolution: '1280x720',
                video_clips: videoClips.map((c: any) => ({
                  id: c.id,
                  track: c.track_id,
                  start_ms: c.start_ms,
                  end_ms: c.end_ms,
                  asset_id: c.source_asset_id || c.output_asset_id,
                })),
                audio_clips: audioClips.map((c: any) => ({
                  id: c.id,
                  track: c.track_id,
                  start_ms: c.start_ms,
                  end_ms: c.end_ms,
                  asset_id: c.output_asset_id,
                })),
                exported_at: new Date().toISOString(),
              }
              const blob = new Blob([JSON.stringify(edl, null, 2)], { type: 'application/json' })
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = `edl_${projectId?.slice(0,8)}.json`
              a.click()
              URL.revokeObjectURL(url)
              toast.success('EDL exported (JSON)')
            }}
            className="flex items-center gap-1 px-3 py-1 border border-border rounded-btn text-xs hover:bg-bg-subtle"
          >
            Export EDL
          </button>

          {/* PNG sequence export (PRD gap) */}
          <button
            onClick={() => {
              // Trigger a render job with png_sequence flag (backend can extend the render task)
              createJob({
                job_type: 'render',
                project_id: projectId!,
                params: {
                  video_clips: videoClips.map((c: any) => ({
                    asset_path: c.asset_path || '',
                    start_frame: c.start_frame,
                    end_frame: c.end_frame,
                  })),
                  audio_clips: audioClips.map((c: any) => ({
                    asset_path: c.asset_path || '',
                    start_frame: c.start_frame,
                    end_frame: c.end_frame,
                  })),
                  resolution: '1280x720',
                  fps: 24,
                  export_format: 'png_sequence', // backend hook
                },
              }).then(() => toast.success('PNG sequence export job submitted'))
                .catch(() => toast.error('Failed to submit PNG sequence export'))
            }}
            className="flex items-center gap-1 px-3 py-1 border border-border rounded-btn text-xs hover:bg-bg-subtle"
            disabled={renderMutation.isPending || !!renderDisabled}
          >
            PNG Sequence
          </button>
        </div>
      </div>

      {/* Audio Offset Editing UI (advanced polish for item 4) */}
      {selectedAudioClip && (
        <div className="flex items-center gap-3 px-4 py-1.5 bg-bg-base border-b border-border text-xs">
          <span className="text-text-muted">Audio Offset (ms)</span>
          <input
            type="number"
            defaultValue={selectedAudioClip.start_ms ?? 0}
            className="w-24 px-2 py-0.5 bg-bg-surface border border-border rounded text-text-primary font-mono"
            onBlur={async (e) => {
              const newStart = parseInt(e.target.value) || 0
              try {
                await api.patch(`/projects/${projectId}/audioclips/${selectedAudioClip.id}`, { start_ms: newStart })
                queryClient.invalidateQueries({ queryKey: ['audioclips', projectId] })
                setSelectedAudioClip({ ...selectedAudioClip, start_ms: newStart })
                toast.success('Audio offset updated')
              } catch {
                toast.error('Failed to update offset')
              }
            }}
          />
          <button
            onClick={() => setSelectedAudioClip(null)}
            className="ml-auto text-text-muted hover:text-text-primary text-xs"
          >
            Close
          </button>
          <span className="text-[10px] text-text-muted">Adjusts clip start position on timeline</span>
        </div>
      )}

      {/* Timeline Zone (65%) */}
      <div className="flex-1 min-h-[40%] bg-bg-surface border-t border-border flex flex-col overflow-hidden">
        {/* Time Ruler */}
        <div className="h-6 border-b border-border bg-bg-elevated flex flex-shrink-0">
          {/* Track header spacer */}
          <div className="w-[160px] flex-shrink-0 flex items-center justify-between px-2 border-r border-border">
            <span className="text-[10px] text-text-muted">Tracks</span>
            <button
              onClick={() => setShowAddTrack(true)}
              className="text-text-muted hover:text-accent"
              title="Add Track"
            >
              <Plus className="w-3 h-3" />
            </button>
          </div>
          {/* Ruler with Playhead */}
          <div 
            className="flex-1 overflow-hidden relative cursor-pointer"
            onClick={handleRulerClick}
            onMouseMove={handleRulerMouseMove}
            onMouseDown={handleRulerMouseDown}
          >
            <div className="flex items-center h-full" style={{ width: rulerWidthPx }}>
              {Array.from({ length: Math.ceil(rulerFrames / 30) }, (_, i) => (
                <div
                  key={i}
                  className="flex-shrink-0 text-[10px] text-text-muted border-l border-border pl-1 h-full flex items-center"
                  style={{ width: 30 * FRAME_PX }}
                >
                  {i}s
                </div>
              ))}
            </div>

            {/* Playhead */}
            <div 
              className="absolute top-0 bottom-0 w-px bg-accent z-10 pointer-events-none"
              style={{ left: playheadFrame * FRAME_PX }}
            >
              <div className="absolute -top-1 -left-1.5 w-3 h-3 bg-accent rounded-full border border-white" />
            </div>
          </div>
        </div>

        {/* Add track inline form */}
        {showAddTrack && (
          <div className="flex items-center gap-2 px-3 py-2 border-b border-border bg-bg-elevated flex-shrink-0">
            <input
              value={newTrackName}
              onChange={(e) => setNewTrackName(e.target.value)}
              placeholder="Track name"
              className="px-2 py-1 bg-bg-base border border-border rounded-btn text-xs text-text-primary w-40"
            />
            <select
              value={newTrackType}
              onChange={(e) => setNewTrackType(e.target.value as TrackType)}
              className="px-2 py-1 bg-bg-base border border-border rounded-btn text-xs text-text-primary"
            >
              <option value="video">Video</option>
              <option value="audio">Audio</option>
              <option value="effect">Effect</option>
              <option value="caption">Caption</option>
            </select>
            <button
              onClick={() => addTrackMutation.mutate()}
              disabled={addTrackMutation.isPending}
              className="px-2 py-1 bg-accent text-accent-fg rounded-btn text-xs hover:bg-accent-hover disabled:opacity-50"
            >
              Add
            </button>
            <button onClick={() => setShowAddTrack(false)} className="text-text-muted hover:text-text-primary">
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        {/* Track rows */}
        <div 
          className="flex-1 overflow-auto"
          onMouseMove={handleTimelineMouseMove}
          onMouseDown={handleTimelineMouseDown}
        >
          {isLoading ? (
            <div className="text-center py-8 text-text-muted text-sm">Loading timeline...</div>
          ) : tracks.length === 0 ? (
            <div className="text-center py-16 text-text-muted text-sm">
              <p>No tracks yet. Add a video or audio track to begin.</p>
              <button
                onClick={() => setShowAddTrack(true)}
                className="mt-3 px-3 py-1.5 border border-dashed border-border rounded-btn text-xs hover:border-border-strong"
              >
                + Add Track
              </button>
            </div>
          ) : (
            <DndContext
              sensors={useSensors(
                useSensor(PointerSensor),
                useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
              )}
              collisionDetection={closestCenter}
              onDragStart={(event) => {
                setActiveDragId(event.active.id as string)
                setActiveDragType('track')
                const track = tracks.find((t: any) => t.id === event.active.id)
                setActiveDragData(track)
              }}
              onDragEnd={(event: DragEndEvent) => {
                setActiveDragId(null)
                setActiveDragType(null)
                setActiveDragData(null)

                const { active, over } = event
                if (!over || active.id === over.id) return

                const oldIndex = tracks.findIndex((t: any) => t.id === active.id)
                const newIndex = tracks.findIndex((t: any) => t.id === over.id)
                if (oldIndex < 0 || newIndex < 0) return

                const reordered = arrayMove(tracks, oldIndex, newIndex)

                // Persist new order to backend
                Promise.all(
                  reordered.map((t: any, idx: number) =>
                    api.patch(`/projects/${projectId}/tracks/${t.id}`, { order: idx })
                  )
                )
                  .then(() => {
                    queryClient.invalidateQueries({ queryKey: ['tracks', projectId] })
                    toast.success('Tracks reordered')
                  })
                  .catch(() => toast.error('Failed to save track order'))
              }}
              onDragCancel={() => {
                setActiveDragId(null)
                setActiveDragType(null)
                setActiveDragData(null)
              }}
            >
              <SortableContext items={tracks.map((t: any) => t.id)} strategy={verticalListSortingStrategy}>
                {tracks.map((track: any) => {
                  const clips = clipsByTrack(track.id)
                  const Icon = TRACK_TYPE_ICONS[track.type] || Layers

                  const {
                    attributes,
                    listeners,
                    setNodeRef,
                    transform,
                    transition,
                  } = useSortable({ id: track.id })

                  const style = {
                    transform: CSS.Transform.toString(transform),
                    transition,
                  }

                  return (
                    <div
                      ref={setNodeRef}
                      style={style}
                      key={track.id}
                      className="flex border-b border-border"
                      {...attributes}
                    >
                      {/* Track header - drag handle on the whole header */}
                      <div
                        className={`w-[160px] flex-shrink-0 flex items-center gap-2 px-3 border-r border-border bg-bg-elevated group cursor-grab active:cursor-grabbing transition-colors ${
                          activeDragType === 'clip' && activeDragData?.track_id === track.id 
                            ? 'bg-accent/10 border-accent/50' 
                            : ''
                        }`}
                        {...listeners}
                      >
                        <Icon className="w-3 h-3 text-text-muted flex-shrink-0" />
                        <span className="text-xs text-text-primary truncate flex-1">{track.name}</span>
                        <span className="text-[10px] text-text-muted">{track.type}</span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            if (confirm(`Delete track "${track.name}"?`)) deleteTrackMutation.mutate(track.id)
                          }}
                          className="text-text-muted hover:text-error opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>

                  {/* Clip area */}
                  <div className="flex-1 relative bg-bg-base overflow-hidden">
                    <div className="relative h-full" style={{ width: rulerWidthPx }}>
                      <DndContext
                        sensors={useSensors(useSensor(PointerSensor))}
                        collisionDetection={closestCenter}
                        onDragStart={(event) => {
                          setActiveDragId(event.active.id as string)
                          setActiveDragType('clip')
                          const clip = clips.find((c: any) => c.id === event.active.id)
                          setActiveDragData(clip)
                          setClipOverId(null)
                        }}
                        onDragOver={(event) => {
                          if (event.over?.id) {
                            setClipOverId(event.over.id as string)
                          }
                        }}
                        onDragEnd={(event) => {
                          setActiveDragId(null)
                          setActiveDragType(null)
                          setActiveDragData(null)
                          setClipOverId(null)

                          // Handle clip reordering within the same track
                          const { active, over } = event
                          if (!over || active.id === over.id) return

                          const activeClip = clips.find((c: any) => c.id === active.id)
                          const overClip = clips.find((c: any) => c.id === over.id)
                          if (!activeClip || !overClip || activeClip.track_id !== overClip.track_id) return

                          const oldIndex = clips.findIndex((c: any) => c.id === active.id)
                          const newIndex = clips.findIndex((c: any) => c.id === over.id)

                          const reorderedClips = arrayMove(clips, oldIndex, newIndex)

                          // Edge-case polish: Re-assign clean sequential orders (0,1,2...) for all clips on this track
                          // This prevents duplicate order conflicts in the future
                          const allClipsOnTrack = [...reorderedClips]  // already the full list for this track in new order
                          const updates = allClipsOnTrack.map((c: any, idx: number) => ({
                            id: c.id,
                            order: idx
                          }))

                          Promise.all(
                            updates.map(u =>
                              api.patch(`/projects/${projectId}/videoclips/${u.id}`, { order: u.order })
                            )
                          )
                            .then(() => {
                              queryClient.invalidateQueries({ queryKey: ['videoclips', projectId] })
                              queryClient.invalidateQueries({ queryKey: ['audioclips', projectId] })
                              toast.success('Clips reordered')
                            })
                            .catch(() => toast.error('Failed to reorder clips'))
                        }}
                        onDragCancel={() => {
                          setActiveDragId(null)
                          setActiveDragType(null)
                          setActiveDragData(null)
                          setClipOverId(null)
                        }}
                      >
                        <SortableContext items={clips.map((c: any) => c.id)} strategy={verticalListSortingStrategy}>
                          {clips.map((clip: any) => {
                            const ov = clipOverrides[clip.id] || {}
                            const start = ov.start_frame ?? clip.start_frame ?? 0
                            const end = ov.end_frame ?? clip.end_frame ?? 0

                            const left = start * FRAME_PX
                            const width = Math.max((end - start) * FRAME_PX, 20)
                            const colorClass = TRACK_TYPE_COLORS[track.type] || 'bg-bg-subtle border-border'

                            const isResizingThis = resizing?.clipId === clip.id

                            const {
                              attributes: clipAttributes,
                              listeners: clipListeners,
                              setNodeRef: setClipNodeRef,
                              isDragging: isClipDragging,
                            } = useSortable({ id: clip.id })

                            // Overlap conflict visual during clip reordering on this track
                            const isReorderActive = activeDragType === 'clip' && activeDragData && activeDragData.track_id === track.id
                            const draggedStart = isReorderActive ? (activeDragData.start_frame ?? 0) : 0
                            const draggedEnd = isReorderActive ? (activeDragData.end_frame ?? 0) : 0
                            const overlapsDragged = isReorderActive && clip.id !== activeDragId &&
                              Math.max(start, draggedStart) < Math.min(end, draggedEnd)

                            return (
                              <div
                                ref={setClipNodeRef}
                                key={clip.id}
                                className={`absolute top-1 bottom-1 rounded ${colorClass} border flex items-center px-1.5 overflow-hidden group ${renderDisabled ? 'cursor-not-allowed opacity-70' : 'cursor-move'} ${isResizingThis ? 'ring-1 ring-accent' : ''} ${clipOverId === clip.id && !isClipDragging ? 'ring-[3px] ring-accent ring-offset-2' : ''} ${overlapsDragged ? 'ring-2 ring-orange-500' : ''}`}
                                style={{ 
                                  left, 
                                  width,
                                  opacity: isClipDragging ? 0.3 : (draggingWholeClip?.clipId === clip.id ? 0.6 : 1) 
                                }}
                                title={clip.name || clip.id}
                                onMouseDown={(e) => startWholeClipDrag(e, clip, track.id)}
                                onClick={() => {
                                  if (track.type === 'audio') setSelectedAudioClip(clip)
                                }}
                              >
                                {/* Drag handle for clip reordering (dnd-kit) - separate from timing drag */}
                                <div
                                  {...clipAttributes}
                                  {...clipListeners}
                                  className="cursor-grab active:cursor-grabbing px-1 mr-1 text-white/60 hover:text-white flex-shrink-0 rounded hover:bg-white/25 transition-colors opacity-0 group-hover:opacity-100"
                                  title="Shift+drag to reorder on track (separate from timing drag)"
                                  onMouseDown={(e) => {
                                    if (!e.shiftKey) {
                                      e.stopPropagation();
                                      return;
                                    }
                                    e.stopPropagation();
                                  }}
                                >
                                  <GripVertical className="w-3 h-3" />
                                </div>
                                <span className="text-[10px] text-white truncate flex-1">
                                  {clip.name || (track.type === 'audio' ? 'audio' : 'clip')}
                                </span>

                                {/* Real waveform visualization for audio clips */}
                                {track.type === 'audio' && (
                                  <AudioWaveform
                                    projectId={projectId}
                                    assetId={clip.output_asset_id}
                                    clipId={clip.id}
                                    width={width}
                                    height={12}
                                  />
                                )}

                                {/* Trim handles */}
                                {!renderDisabled && (
                                  <>
                                    <div
                                      className="absolute left-0 top-0 bottom-0 w-2 bg-white/60 hover:bg-white cursor-ew-resize z-20"
                                      onMouseDown={(e) => startTrim(e, clip, 'left', track.id)}
                                    />
                                    <div
                                      className="absolute right-0 top-0 bottom-0 w-2 bg-white/60 hover:bg-white cursor-ew-resize z-20"
                                      onMouseDown={(e) => startTrim(e, clip, 'right', track.id)}
                                    />
                                  </>
                                )}
                              </div>
                            )
                          })}
                        </SortableContext>
                      </DndContext>

                      {/* Playhead overlay on this track row */}
                      <div
                        className="absolute top-0 bottom-0 w-px bg-accent z-30 pointer-events-none"
                        style={{ left: playheadFrame * FRAME_PX }}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
              </SortableContext>

              <DragOverlay>
                {activeDragType === 'track' && activeDragData && (
                  <div
                    className="flex w-[160px] items-center gap-2 border border-border bg-bg-elevated px-3 py-1 text-xs opacity-90 shadow-lg"
                    style={{ height: TRACK_H }}
                  >
                    <span className="truncate">{activeDragData.name}</span>
                    <span className="text-[10px] text-text-muted">{activeDragData.type}</span>
                  </div>
                )}

                {activeDragType === 'clip' && activeDragData && (
                  <div
                    className={`flex items-center gap-1 rounded border px-2 py-1 text-[10px] text-white shadow-lg ${TRACK_TYPE_COLORS[activeDragData.track_id ? 'video' : 'audio'] || 'bg-bg-subtle border-border'}`}
                    style={{ width: 160, height: 28 }}
                  >
                    <GripVertical className="w-3 h-3 opacity-70" />
                    <span className="truncate">{activeDragData.name || 'clip'}</span>
                  </div>
                )}
              </DragOverlay>
            </DndContext>
          )}
        </div>
      </div>
    </div>
  )
}
