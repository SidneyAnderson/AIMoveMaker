import api from './client'

export async function getStoryboard(projectId: string) {
  const res = await api.get(`/projects/${projectId}/storyboard/`)
  return res.data
}

export async function listKeyframes(projectId: string) {
  const res = await api.get(`/projects/${projectId}/keyframes/`)
  return res.data
}

export async function createKeyframe(projectId: string, data: Record<string, unknown>) {
  const res = await api.post(`/projects/${projectId}/keyframes/`, data)
  return res.data
}

export async function updateKeyframe(projectId: string, keyframeId: string, data: Record<string, unknown>) {
  const res = await api.patch(`/projects/${projectId}/keyframes/${keyframeId}`, data)
  return res.data
}

export async function deleteKeyframe(projectId: string, keyframeId: string) {
  await api.delete(`/projects/${projectId}/keyframes/${keyframeId}`)
}
