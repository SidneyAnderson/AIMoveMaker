import api from './client'

export async function listProjects(skip = 0, limit = 100) {
  const res = await api.get('/projects/', { params: { skip, limit } })
  return res.data
}

export async function getProject(id: string) {
  const res = await api.get(`/projects/${id}`)
  return res.data
}

export async function createProject(data: { name: string; description?: string }) {
  const res = await api.post('/projects/', data)
  return res.data
}

export async function updateProject(id: string, data: Record<string, unknown>) {
  const res = await api.patch(`/projects/${id}`, data)
  return res.data
}

export async function deleteProject(id: string) {
  await api.delete(`/projects/${id}`)
}

export async function listMembers(projectId: string) {
  const res = await api.get(`/projects/${projectId}/members`)
  return res.data
}

export async function addMember(projectId: string, userId: string, role: string) {
  const res = await api.post(`/projects/${projectId}/members`, { user_id: userId, role })
  return res.data
}

export async function removeMember(projectId: string, userId: string) {
  await api.delete(`/projects/${projectId}/members/${userId}`)
}
