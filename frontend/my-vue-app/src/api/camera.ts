import api from './request'

const API_BASE = 'http://localhost:8000'
const WS_BASE = API_BASE.replace(/^http/, 'ws')

export const cameraApi = {
  // 创建会话
  createSession: (animal_type_id?: number) =>
    api.post('/api/camera/session', { animal_type_id }),

  // 获取会话状态
  getSession: (session_id: string) =>
    api.get(`/api/camera/session/${session_id}`),

  // 停止会话
  stopSession: (session_id: string) =>
    api.delete(`/api/camera/session/${session_id}`),

  // WebSocket URL
  getWsUrl: (session_id: string) => {
    const token = localStorage.getItem('token')
    const suffix = token ? `?token=${encodeURIComponent(token)}` : ''
    return `${WS_BASE}/api/camera/ws/${session_id}${suffix}`
  },
}
