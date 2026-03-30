import api from './request'

export const statisticsApi = {
  getOverview: () => api.get('/api/statistics/overview'),
  getTrend: (days = 7) => api.get('/api/statistics/trend', { params: { days } }),
  getByAnimalType: () => api.get('/api/statistics/by-animal-type'),
  getHealthDistribution: (animal_type_id?: number) =>
    api.get('/api/statistics/health-distribution', {
      params: animal_type_id ? { animal_type_id } : {}
    }),
}

export const animalsApi = {
  list: (params?: { page?: number; page_size?: number; animal_type_id?: number; keyword?: string }) =>
    api.get('/api/animals/', { params }),
  create: (data: any) => api.post('/api/animals/', data),
  get: (id: number) => api.get(`/api/animals/${id}`),
  update: (id: number, data: any) => api.put(`/api/animals/${id}`, data),
  delete: (id: number) => api.delete(`/api/animals/${id}`),
}
