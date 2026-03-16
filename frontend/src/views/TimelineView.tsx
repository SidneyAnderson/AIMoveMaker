import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useProjectStore } from '@/stores/projectStore'
import { useEffect, useState } from 'react'
import { Play, SkipBack, SkipForward, StepBack, StepForward, Download, Plus, X, Film, Music, Layers } from 'lucide-react'
import { toast } from 'sonner'
import api from '@/api/client'
import { createJob } from '@/api/jobs'

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

export default function TimelineView() {
  const { projectId } = useParams<{ projectId: string }>()
  const queryClient = useQueryClient()
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject)

  const [showAddTrack, setShowAddTrack] = useState(false)
  const [newTrackName, setNewTrackName] = useState('')
  const [newTrackType, setNewTrackType] = useState<TrackType>('video')

  useEffect(() => {
    if (projectId) setCurrentProject(projectId)
    return () => setCurrentProject(null)
  }, [projectId])

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
    mutationFn: () => createJob({ job_type: 'render', project_id: projectId!, params: {} }),
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
          <span className="text-xs text-text-muted font-mono ml-4">00:00:00:00</span>
          <button
            onClick={() => renderMutation.mutate()}
            disabled={renderMutation.isPending}
            className="ml-auto mr-4 flex items-center gap-1 px-3 py-1 bg-accent text-accent-fg rounded-btn text-xs hover:bg-accent-hover disabled:opacity-50"
          >
            <Download className="w-3 h-3" /> {renderMutation.isPending ? 'Submitting...' : 'Render'}
          </button>
        </div>
      </div>

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
          {/* Ruler */}
          <div className="flex-1 overflow-hidden">
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
        <div className="flex-1 overflow-auto">
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
            tracks.map((track: any) => {
              const clips = clipsByTrack(track.id)
              const Icon = TRACK_TYPE_ICONS[track.type] || Layers
              return (
                <div key={track.id} className="flex border-b border-border" style={{ height: TRACK_H }}>
                  {/* Track header */}
                  <div className="w-[160px] flex-shrink-0 flex items-center gap-2 px-3 border-r border-border bg-bg-elevated group">
                    <Icon className="w-3 h-3 text-text-muted flex-shrink-0" />
                    <span className="text-xs text-text-primary truncate flex-1">{track.name}</span>
                    <span className="text-[10px] text-text-muted">{track.type}</span>
                    <button
                      onClick={() => {
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
                      {clips.map((clip: any) => {
                        const left = (clip.start_frame ?? 0) * FRAME_PX
                        const width = Math.max(((clip.end_frame ?? 0) - (clip.start_frame ?? 0)) * FRAME_PX, 20)
                        const colorClass = TRACK_TYPE_COLORS[track.type] || 'bg-bg-subtle border-border'
                        return (
                          <div
                            key={clip.id}
                            className={`absolute top-1 bottom-1 rounded ${colorClass} border flex items-center px-1.5 overflow-hidden cursor-pointer hover:brightness-110`}
                            style={{ left, width }}
                            title={clip.name || clip.id}
                          >
                            <span className="text-[10px] text-white truncate">
                              {clip.name || 'clip'}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
