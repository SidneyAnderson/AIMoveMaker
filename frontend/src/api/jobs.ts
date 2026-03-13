import api from './client'

export async function listJobs(params?: Record<string, string>) {
  const res = await api.get('/jobs/', { params })
  return res.data
}

export async function createJob(data: Record<string, unknown>) {
  const res = await api.post('/jobs/', data)
  return res.data
}

export async function getJob(jobId: string) {
  const res = await api.get(`/jobs/${jobId}`)
  return res.data
}

export async function cancelJob(jobId: string) {
  const res = await api.patch(`/jobs/${jobId}`, { status: 'cancelled' })
  return res.data
}
