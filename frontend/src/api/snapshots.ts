import api from './client'

export interface Snapshot {
  id: string
  project_id: string
  type: string
  tier: 'auto' | 'manual' | 'major' | 'handoff'
  label?: string
  created_at: string
  size_bytes?: number
  created_by?: string
}

export interface SnapshotListResponse {
  items: Snapshot[]
  total: number
}

export async function listSnapshots(projectId: string, tier?: string): Promise<SnapshotListResponse> {
  const res = await api.get(`/projects/${projectId}/snapshots/`, { params: tier ? { tier } : {} })
  return res.data
}

export async function createSnapshot(projectId: string, data: { type?: string; tier?: string; label?: string }) {
  const res = await api.post(`/projects/${projectId}/snapshots/`, data)
  return res.data
}

export async function restoreSnapshot(projectId: string, snapshotId: string) {
  const res = await api.post(`/projects/${projectId}/snapshots/${snapshotId}/restore`)
  return res.data
}
