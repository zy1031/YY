import api from './request'

function resolveExtension(contentType: string) {
  if (contentType.includes('avi')) return 'avi'
  if (contentType.includes('quicktime')) return 'mov'
  if (contentType.includes('webm')) return 'webm'
  return 'mp4'
}

async function fetchVideoBlob(record_id: number) {
  const token = localStorage.getItem('token')
  const response = await fetch(`http://localhost:8000/api/video/${record_id}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || '视频获取失败')
  }

  const blob = await response.blob()
  const contentType = response.headers.get('content-type') || 'video/mp4'
  const videoBlob = blob.type && blob.type.startsWith('video/') ? blob : new Blob([blob], { type: contentType })
  return {
    blob: videoBlob,
    contentType,
    extension: resolveExtension(contentType),
  }
}

export const videoApi = {
  // 上传视频
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/api/video/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 提交检测任务
  detect: (file_path: string, animal_type_id?: number, sample_interval = 5) => {
    const form = new FormData()
    form.append('file_path', file_path)
    form.append('sample_interval', String(sample_interval))
    if (animal_type_id) form.append('animal_type_id', String(animal_type_id))
    return api.post('/api/video/detect', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 查询任务进度
  getTaskProgress: (task_id: string) =>
    api.get(`/api/video/task/${task_id}`),

  // 获取视频记录列表
  listRecords: (page = 1, page_size = 10) =>
    api.get('/api/video/records', { params: { page, page_size } }),

  // 获取跟踪轨迹
  getTracks: (record_id: number) =>
    api.get(`/api/video/${record_id}/tracks`),

  // 下载结果视频
  downloadVideo: async (record_id: number) => {
    const { blob, extension } = await fetchVideoBlob(record_id)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `video_detection_${record_id}.${extension}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  },

  // 获取结果视频播放地址
  getVideoPreviewUrl: async (record_id: number) => {
    const { blob } = await fetchVideoBlob(record_id)
    return URL.createObjectURL(blob)
  },
}
