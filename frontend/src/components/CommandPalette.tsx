import { Command } from 'cmdk'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { FolderKanban, Settings, Users, Plus, Search } from 'lucide-react'

interface CommandPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate()

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        onOpenChange(!open)
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onOpenChange])

  if (!open) return null

  const runCommand = (cmd: () => void) => {
    onOpenChange(false)
    cmd()
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-start justify-center pt-[20vh]">
      <Command
        className="w-full max-w-lg bg-bg-elevated border border-border rounded-card shadow-2xl overflow-hidden"
        onKeyDown={(e) => {
          if (e.key === 'Escape') onOpenChange(false)
        }}
      >
        <div className="flex items-center gap-2 px-4 border-b border-border">
          <Search className="w-4 h-4 text-text-muted" />
          <Command.Input
            placeholder="Type a command or search..."
            className="w-full py-3 bg-transparent text-text-primary text-sm outline-none placeholder:text-text-muted"
          />
        </div>
        <Command.List className="max-h-80 overflow-auto p-2">
          <Command.Empty className="py-6 text-center text-sm text-text-muted">
            No results found.
          </Command.Empty>
          <Command.Group heading="Navigation" className="text-xs text-text-muted px-2 py-1">
            <Command.Item
              className="flex items-center gap-2 px-2 py-2 text-sm text-text-primary rounded cursor-pointer data-[selected=true]:bg-accent-subtle"
              onSelect={() => runCommand(() => navigate('/projects'))}
            >
              <FolderKanban className="w-4 h-4" /> Projects
            </Command.Item>
            <Command.Item
              className="flex items-center gap-2 px-2 py-2 text-sm text-text-primary rounded cursor-pointer data-[selected=true]:bg-accent-subtle"
              onSelect={() => runCommand(() => navigate('/admin'))}
            >
              <Users className="w-4 h-4" /> Admin Panel
            </Command.Item>
            <Command.Item
              className="flex items-center gap-2 px-2 py-2 text-sm text-text-primary rounded cursor-pointer data-[selected=true]:bg-accent-subtle"
              onSelect={() => runCommand(() => navigate('/settings'))}
            >
              <Settings className="w-4 h-4" /> Settings
            </Command.Item>
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  )
}
