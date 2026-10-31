import request from '@/utils/request'

export const evaluationsApi = {
  getCampaigns() {
    return request.get('/evaluations/campaigns/')
  },
  getParticipants() {
    return request.get('/evaluations/campaigns/participants/')
  },
  createCampaign(data) {
    return request.post('/evaluations/campaigns/', data)
  },
  publishCampaign(id) {
    return request.post(`/evaluations/campaigns/${id}/publish/`)
  },
  closeCampaign(id) {
    return request.post(`/evaluations/campaigns/${id}/close/`)
  },
  getMyTasks() {
    return request.get('/evaluations/tasks/my/')
  },
  submitTask(campaignId, targetId, data) {
    return request.post(`/evaluations/tasks/${campaignId}/${targetId}/submit/`, data)
  },
  getResults(campaignId) {
    return request.get(`/evaluations/campaigns/${campaignId}/results/`)
  }
}
