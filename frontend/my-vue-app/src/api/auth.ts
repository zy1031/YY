import api from './request'

export const authApi = {
  register: (data: { username: string; password: string; email?: string }) =>
    api.post('/api/auth/register', data),

  login: (data: { username: string; password: string }) =>
    api.post('/api/auth/login', data),

  logout: () =>
    api.post('/api/auth/logout'),

  getProfile: () =>
    api.get('/api/auth/profile'),
}
