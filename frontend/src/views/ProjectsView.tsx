import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listProjects, createProject, deleteProject } from '@/api/projects'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { Plus, Trash2, FolderKanban } from 'lucide-react'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/authStore'

export default function ProjectsView() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.global_role === 'admin'
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => listProjects(),
  })

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description?: string }) => createProject(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setShowCreate(false)
      setName('')
      setDescription('')
      toast.success('Project created')
    },
    onError: () => toast.error('Failed to create project'),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      toast.success('Project deleted')
    },
  })

  const projects = data?.projects || []

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold text-text-primary">Projects</h1>
        {isAdmin && (
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-3 py-2 bg-accent text-accent-fg rounded-btn text-sm hover:bg-accent-hover"
          >
            <Plus className="w-4 h-4" /> New Project
          </button>
        )}
      </div>

      {showCreate && (
        <div className="mb-6 p-4 bg-bg-surface border border-border rounded-card">
          <h2 className="text-sm font-medium mb-3">Create Project</h2>
          <div className="space-y-3">
            <input
              placeholder="Project name *"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-bg-base border border-border rounded-btn text-sm"
            />
            <textarea
              placeholder="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-bg-base border border-border rounded-btn text-sm"
              rows={2}
            />
            <div className="flex gap-2">
              <button
                onClick={() => createMutation.mutate({ name, description })}
                disabled={!name}
                className="px-3 py-1.5 bg-accent text-accent-fg rounded-btn text-sm disabled:opacity-50"
              >
                Create
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="px-3 py-1.5 border border-border rounded-btn text-sm text-text-secondary"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-text-muted text-sm">Loading...</div>
      ) : projects.length === 0 ? (
        <div className="text-center py-16 text-text-muted">
          <FolderKanban className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>No projects yet</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project: any) => (
            <div
              key={project.id}
              className="p-4 bg-bg-surface border border-border rounded-card hover:border-border-strong cursor-pointer transition-colors group"
              onClick={() => navigate(`/projects/${project.id}/storyboard`)}
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-medium text-text-primary">{project.name}</h3>
                  <p className="text-sm text-text-secondary mt-1">{project.description || 'No description'}</p>
                </div>
                {isAdmin && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      if (confirm('Delete this project?'))
                        deleteMutation.mutate(project.id)
                    }}
                    className="text-text-muted hover:text-error opacity-0 group-hover:opacity-100"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
              <div className="mt-3 flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded-tag ${
                  project.state === 'CreativeActive' ? 'bg-accent-subtle text-accent' :
                  project.state === 'EngActive' ? 'bg-green-900/30 text-success' :
                  project.state === 'Completed' ? 'bg-green-900/30 text-success' :
                  'bg-bg-subtle text-text-muted'
                }`}>
                  {project.state || 'Draft'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
