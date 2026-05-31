import api from './client'

export interface Asset {
  id: string
  project_id: string
  job_id?: string | null
  type: string
  subtype: string
  mime_type: string
  width?: number | null
  height?: number | null
  duration_ms?: number | null
  file_size_bytes: number
  created_at: string
}

export interface AssetListResponse {
  items: Asset[]
  total: number
  page: number
  page_size: number
  pages: number
}

/**
 * Upload a file as a project asset.
 * Returns the created Asset record (storage_path is intentionally excluded per PRD).
 */
export async function uploadAsset(projectId: string, file: File): Promise<Asset> {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post(`/projects/${projectId}/assets/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

/**
 * List assets for a project.
 */
export async function listAssets(projectId: string): Promise<AssetListResponse> {
  const res = await api.get(`/projects/${projectId}/assets/`)
  return res.data
}

/**
 * Get a single asset metadata.
 */
export async function getAsset(projectId: string, assetId: string): Promise<Asset> {
  const res = await api.get(`/projects/${projectId}/assets/${assetId}`)
  return res.data
}

/**
 * Returns the authenticated download URL for an asset image/file.
 * Use with <img src={...} /> or fetch() + blob for canvas.
 * The axios client automatically injects the Authorization header on direct api calls,
 * but for native <img> tags we rely on the browser sending cookies or we fetch as blob.
 */
export function getAssetDownloadUrl(projectId: string, assetId: string): string {
  return `/api/projects/${projectId}/assets/${assetId}/download`
}

/**
 * Fetch an asset as a Blob (useful for loading into <canvas> or Image).
 * Handles auth via the shared axios client.
 */
export async function fetchAssetAsBlob(projectId: string, assetId: string): Promise<Blob> {
  const res = await api.get(getAssetDownloadUrl(projectId, assetId).replace('/api', ''), {
    responseType: 'blob',
  })
  return res.data
}

/**
 * Convenience: load an asset directly into an HTMLImageElement (for canvas drawImage).
 * Returns a promise that resolves when the image is loaded.
 */
export async function loadAssetImage(projectId: string, assetId: string): Promise<HTMLImageElement> {
  const blob = await fetchAssetAsBlob(projectId, assetId)
  const url = URL.createObjectURL(blob)

  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = reject
    img.src = url
  })
}
