import request from '@/utils/request'

export const knowingPeopleApi = {
  getOptions() {
    return request.get('/knowing-people/options/')
  },
  previewCampaign(data) {
    return request.post('/knowing-people/campaigns/preview/', data)
  },
  getCampaigns() {
    return request.get('/knowing-people/campaigns/')
  },
  createCampaign(data) {
    return request.post('/knowing-people/campaigns/', data)
  },
  closeCampaign(id) {
    return request.post(`/knowing-people/campaigns/${id}/close/`)
  },
  getProgress(id, params) {
    return request.get(`/knowing-people/campaigns/${id}/progress/`, { params })
  },
  getStatisticsExport(id) {
    return request.get(`/knowing-people/campaigns/${id}/statistics-export/`, { responseType: 'blob' })
  },
  getMyTasks() {
    return request.get('/knowing-people/tasks/my/')
  },
  getTask(id) {
    return request.get(`/knowing-people/tasks/${id}/`)
  },
  saveDraft(id, payload) {
    return request.post(`/knowing-people/tasks/${id}/save-draft/`, { payload })
  },
  submitTask(id, payload) {
    return request.post(`/knowing-people/tasks/${id}/submit/`, { payload })
  },
  returnTask(id, reason) {
    return request.post(`/knowing-people/tasks/${id}/return/`, { reason })
  },
  remindTask(id) {
    return request.post(`/knowing-people/tasks/${id}/remind/`)
  }
}
