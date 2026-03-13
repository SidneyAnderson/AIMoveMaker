import api from './client'

export async function login(email: string, password: string) {
  const params = new URLSearchParams()
  params.append('username', email)
  params.append('password', password)
  const res = await api.post('/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return res.data
}

export async function register(data: {
  email: string
  password: string
  full_name: string
  invite_token?: string
}) {
  const res = await api.post('/auth/register', data)
  return res.data
}

export async function refreshTokens(refreshToken: string) {
  const res = await api.post('/auth/refresh', { refresh_token: refreshToken })
  return res.data
}

export async function changePassword(currentPassword: string, newPassword: string) {
  const res = await api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
  return res.data
}
