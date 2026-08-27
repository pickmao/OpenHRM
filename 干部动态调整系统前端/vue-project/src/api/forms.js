import request from '@/utils/request'

export const formsApi = {
  getTemplates(params) {
    return request.get('/forms/templates/', { params })
  },
  createTemplate(data) {
    return request.post('/forms/templates/', data, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  updateTemplate(id, data) {
    return request.patch(`/forms/templates/${id}/`, data, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  previewDispatch(data) {
    return request.post('/forms/dispatch/preview/', data)
  },
  publishDispatch(data) {
    return request.post('/forms/dispatch/publish/', data)
  },
  getDispatches() {
    return request.get('/forms/dispatch/')
  },
  getProgress(batchId) {
    return request.get(`/forms/dispatch/${batchId}/progress/`)
  },
  getTaskResults(batchId, params) {
    return request.get(`/forms/dispatch/${batchId}/task-results/`, { params })
  },
  getDashboard(batchId) {
    return request.get(`/forms/dispatch/${batchId}/dashboard/`)
  },
  getPendingUsers(batchId, params) {
    return request.get(`/forms/dispatch/${batchId}/pending-users/`, { params })
  },
  getMyTasks(params) {
    return request.get('/forms/tasks/my/', { params })
  },
  getTask(taskId) {
    return request.get(`/forms/tasks/${taskId}/`)
  },
  saveDraft(taskId, payloadJson = {}, attachmentsJson = []) {
    return request.patch(`/forms/tasks/${taskId}/save-draft/`, {
      payload_json: payloadJson,
      attachments_json: attachmentsJson
    })
  },
  submitTask(taskId, payloadJson = {}, scoreJson = null, attachmentsJson = []) {
    return request.post(`/forms/tasks/${taskId}/submit/`, {
      payload_json: payloadJson,
      score_json: scoreJson,
      attachments_json: attachmentsJson
    })
  },
  returnTask(taskId, reason) {
    return request.post(`/forms/tasks/${taskId}/return/`, { reason })
  },
  getTaskResult(taskId) {
    return request.get(`/forms/tasks/${taskId}/result/`)
  },
  deleteTask(taskId) {
    return request.delete(`/forms/tasks/${taskId}/`)
  },
  getOnlyOfficeConfig(taskId) {
    return request.get(`/forms/tasks/${taskId}/onlyoffice-config/`)
  },
  getOnlyOfficeViewConfig(taskId) {
    return request.get(`/forms/tasks/${taskId}/onlyoffice-view-config/`)
  }
}
