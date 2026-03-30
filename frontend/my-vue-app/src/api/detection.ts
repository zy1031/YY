import api from './request'

export const modelsApi = {
  // 动物类型
  getAnimalTypes: () => api.get('/api/animal-types/'),

  // 模型管理
  listModels: (animal_type_id?: number) =>
    api.get('/api/models/', { params: animal_type_id ? { animal_type_id } : {} }),

  getModel: (id: number) => api.get(`/api/models/${id}`),

  getCurrentModel: () => api.get('/api/models/switch'),

  switchModel: (model_id: number) =>
    api.post('/api/models/switch', { model_id }),

  updateModelConfig: (id: number, data: { confidence_threshold?: number; iou_threshold?: number }) =>
    api.put(`/api/models/${id}/config`, data),
}

export const detectionApi = {
  // 图片上传
  uploadImage: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/api/detection/image/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 图片检测
  detectImage: (file_path: string, animal_type_id?: number) => {
    const form = new FormData()
    form.append('file_path', file_path)
    if (animal_type_id) form.append('animal_type_id', String(animal_type_id))
    return api.post('/api/detection/image/detect', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 获取历史
  getHistory: (params?: { page?: number; page_size?: number; detection_type?: string; animal_type_id?: number }) =>
    api.get('/api/detection/history', { params }),

  // 获取详细结果
  getResults: (id: number) => api.get(`/api/detection/${id}/results`),

  // 删除记录
  deleteRecord: (id: number) => api.delete(`/api/detection/${id}`),
}
