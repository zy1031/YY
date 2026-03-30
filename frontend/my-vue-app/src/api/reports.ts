import api from './request'

export const reportsApi = {
  // 生成报告
  generate: (detection_record_id: number, report_type?: string) =>
    api.post('/api/reports/generate', { detection_record_id, report_type }),

  // 查询生成任务进度
  getTask: (task_id: string) =>
    api.get(`/api/reports/task/${task_id}`),

  // 报告列表
  list: (page = 1, page_size = 10) =>
    api.get('/api/reports/', { params: { page, page_size } }),

  // 报告详情
  get: (id: number) =>
    api.get(`/api/reports/${id}`),

  // 删除报告
  delete: (id: number) =>
    api.delete(`/api/reports/${id}`),

  // 下载报告（Markdown）
  download: (id: number) =>
    window.open(`http://localhost:8000/api/reports/${id}/download`, '_blank'),

  // 下载 PDF 报告
  downloadPdf: (id: number) =>
    window.open(`http://localhost:8000/api/reports/${id}/download/pdf`, '_blank'),
}
