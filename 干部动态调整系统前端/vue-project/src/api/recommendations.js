import request from '@/utils/request'

export const recommendationsApi = {
  getOptions() {
    return request.get('/recommendations/options/')
  },
  previewCampaign(data) {
    return request.post('/recommendations/campaigns/preview/', data)
  },
  getCampaigns() {
    return request.get('/recommendations/campaigns/')
  },
  createCampaign(data) {
    return request.post('/recommendations/campaigns/', data)
  },
  closeCampaign(id) {
    return request.post(`/recommendations/campaigns/${id}/close/`)
  },
  getStats(id) {
    return request.get(`/recommendations/campaigns/${id}/stats/`)
  },
  exportStats(id) {
    return request.get(`/recommendations/campaigns/${id}/stats/export/`, { responseType: 'blob' })
  },
  getMyTasks() {
    return request.get('/recommendations/tasks/my/')
  },
  getTask(id) {
    return request.get(`/recommendations/tasks/${id}/`)
  },
  saveDraft(id, data) {
    return request.post(`/recommendations/tasks/${id}/save-draft/`, data)
  },
  submitTask(id, data) {
    return request.post(`/recommendations/tasks/${id}/submit/`, data)
  }
}
