import { useParams } from 'react-router-dom'
import { useProjectStore } from '@/stores/projectStore'
import { useEffect } from 'react'
import { Play, SkipBack, SkipForward, StepBack, StepForward, Download } from 'lucide-react'

export default function TimelineView() {
  const { projectId } = useParams<{ projectId: string }>()
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject)

  useEffect(() => {
    if (projectId) setCurrentProject(projectId)
    return () => setCurrentProject(null)
  }, [projectId])

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
          <button className="ml-auto mr-4 flex items-center gap-1 px-3 py-1 bg-accent text-accent-fg rounded-btn text-xs hover:bg-accent-hover">
            <Download className="w-3 h-3" /> Render
          </button>
        </div>
      </div>

      {/* Timeline Zone (65%) */}
      <div className="flex-1 min-h-[40%] bg-bg-surface border-t border-border overflow-auto">
        {/* Time Ruler */}
        <div className="h-6 border-b border-border bg-bg-elevated flex items-center px-[160px]">
          {Array.from({ length: 20 }, (_, i) => (
            <div key={i} className="flex-shrink-0 w-16 text-[10px] text-text-muted border-l border-border pl-1">
              {i}s
            </div>
          ))}
        </div>

        {/* Tracks */}
        <div className="text-center py-16 text-text-muted text-sm">
          <p>No tracks yet. Add a video or audio track to begin.</p>
          <button className="mt-3 px-3 py-1.5 border border-dashed border-border rounded-btn text-xs hover:border-border-strong">
            + Add Track
          </button>
        </div>
      </div>
    </div>
  )
}
