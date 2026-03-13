import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listKeyframes } from '@/api/storyboard'
import { useProjectStore } from '@/stores/projectStore'
import { useEffect } from 'react'
import { ImagePlus, Wand2, Send } from 'lucide-react'

export default function StoryboardView() {
  const { projectId } = useParams<{ projectId: string }>()
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject)
  const selectedKeyframeId = useProjectStore((s) => s.selectedKeyframeId)
  const setSelectedKeyframe = useProjectStore((s) => s.setSelectedKeyframe)

  useEffect(() => {
    if (projectId) setCurrentProject(projectId)
    return () => setCurrentProject(null)
  }, [projectId])

  const { data, isLoading } = useQuery({
    queryKey: ['keyframes', projectId],
    queryFn: () => listKeyframes(projectId!),
    enabled: !!projectId,
  })

  const keyframes = data?.keyframes || []

  return (
    <div className="h-full flex flex-col">
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
          <button className="flex items-center gap-1 px-3 py-1.5 bg-accent text-accent-fg rounded-btn text-xs hover:bg-accent-hover">
            <Wand2 className="w-3 h-3" /> Generate All
          </button>
          <button className="flex items-center gap-1 px-3 py-1.5 bg-accent text-accent-fg rounded-btn text-xs hover:bg-accent-hover">
            <Send className="w-3 h-3" /> Submit to Engineering
          </button>
        </div>
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-auto p-4">
        {isLoading ? (
          <div className="text-text-muted text-sm">Loading keyframes...</div>
        ) : keyframes.length === 0 ? (
          <div className="text-center py-16 text-text-muted">
            <ImagePlus className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No keyframes yet. Add one to start your storyboard.</p>
          </div>
        ) : (
          <div className="grid grid-cols-6 gap-3">
            {keyframes.map((kf: any) => (
              <div
                key={kf.id}
                onClick={() => setSelectedKeyframe(kf.id)}
                className={`bg-bg-surface border rounded-card overflow-hidden cursor-pointer transition-all ${
                  selectedKeyframeId === kf.id
                    ? 'border-accent border-2 bg-accent-subtle'
                    : 'border-border hover:border-border-strong'
                }`}
              >
                {/* Thumbnail area */}
                <div className="aspect-square bg-bg-subtle relative">
                  {kf.selected_asset_id ? (
                    <div className="w-full h-full flex items-center justify-center text-text-muted text-xs">
                      Asset
                    </div>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <ImagePlus className="w-6 h-6 text-text-muted opacity-30" />
                    </div>
                  )}
                  <span className="absolute top-1 left-1 text-[10px] bg-bg-base/80 px-1 rounded">
                    {String(kf.index + 1).padStart(2, '0')}
                  </span>
                  <span className={`absolute top-1 right-1 w-2 h-2 rounded-full ${
                    kf.selected_asset_id ? 'bg-success' : 'bg-text-muted'
                  }`} />
                </div>
                {/* Info */}
                <div className="p-2">
                  <p className="text-xs text-text-secondary truncate">
                    {kf.positive_prompt || 'No prompt'}
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
  )
}
