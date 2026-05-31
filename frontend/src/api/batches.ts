import api from './client'

export interface Batch {
  id: string
  project_id: string
  name: string
  job_count: number
  done_count: number
  failed_count: number
  status: 'pending' | 'running' | 'done' | 'partial_failure' | 'failed'
  created_at: string
  created_by: string
}

export interface BatchListResponse {
  items: Batch[]
  total: number
}

export async function listBatches(projectId?: string): Promise<BatchListResponse> {
  const res = await api.get('/batches/', { params: projectId ? { project_id: projectId } : {} })
  return res.data
}

export async function createBatch(data: { project_id: string; name: string; job_ids: string[] }) {
  const res = await api.post('/batches/', data)
  return res.data
}

export async function getBatch(batchId: string) {
  const res = await api.get(`/batches/${batchId}`)
  return res.data
}
