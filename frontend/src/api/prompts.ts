import api from './client'

export interface PromptTemplate {
  id: string
  title: string
  positive_prompt: string
  negative_prompt?: string
  model_id?: string
  params?: any
  scope: 'global' | 'project'
  project_id?: string
  created_by: string
  created_at: string
}

export async function listTemplates(projectId?: string) {
  const res = await api.get('/prompt-templates/', { params: { project_id: projectId } })
  return res.data
}

export async function createTemplate(data: any) {
  const res = await api.post('/prompt-templates/', data)
  return res.data
}

export async function applyTemplate(templateId: string, keyframeId?: string) {
  const res = await api.post(`/prompt-templates/${templateId}/apply`, { keyframe_id: keyframeId })
  return res.data
}

// Prompt History
export interface PromptHistoryEntry {
  id: string
  prompt_text: string
  negative_prompt?: string
  model_id?: string
  params?: any
  job_id?: string
  created_at: string
}

export async function listHistory(projectId?: string) {
  const res = await api.get('/prompt-history/', { params: { project_id: projectId } })
  return res.data
}

export async function createHistory(data: any) {
  const res = await api.post('/prompt-history/', data)
  return res.data
}
