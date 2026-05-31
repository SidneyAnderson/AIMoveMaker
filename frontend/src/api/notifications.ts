import api from './client'

export interface Notification {
  id: string
  user_id: string
  project_id?: string
  type: string
  channel: string
  payload?: any
  sent_at?: string
  delivered: boolean
  read_at?: string
  created_at: string
}

export interface NotificationListResponse {
  items: Notification[]
  total: number
  page: number
  page_size: number
  pages: number
}

export async function listNotifications(): Promise<NotificationListResponse> {
  const res = await api.get('/notifications/')
  return res.data
}

export async function markRead(notificationId: string): Promise<Notification> {
  const res = await api.patch(`/notifications/${notificationId}/read`)
  return res.data
}

export async function markAllRead(): Promise<{ message: string }> {
  const res = await api.patch('/notifications/read-all')
  return res.data
}

// Notification Preferences (full backend support)
export async function getNotificationPreferences(): Promise<any> {
  const res = await api.get('/users/me/notification-preferences')
  return res.data.preferences || {}
}

export async function updateNotificationPreferences(preferences: any): Promise<any> {
  const res = await api.patch('/users/me/notification-preferences', { preferences })
  return res.data.preferences || {}
}
