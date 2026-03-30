import api from './request'

const WS_BASE = 'ws://localhost:8000'

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
  getWsUrl: (session_id: string) =>
    `${WS_BASE}/api/camera/ws/${session_id}`,
}
