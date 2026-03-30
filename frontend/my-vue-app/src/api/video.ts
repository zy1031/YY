import api from './request'

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
  downloadVideo: (record_id: number) =>
    window.open(`http://localhost:8000/api/video/${record_id}/download`, '_blank'),
}
