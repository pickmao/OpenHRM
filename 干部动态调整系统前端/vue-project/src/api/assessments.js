import request from '@/utils/request'

export const assessmentApi = {
  getFiles(params) { return request.get('/assessments/analysis-files/', { params }) },
  uploadFile(data) { return request.post('/assessments/analysis-files/upload-excel/', data, { headers: { 'Content-Type': 'multipart/form-data' } }) },
  updateFile(id, data) { return request.patch(`/assessments/analysis-files/${id}/`, data) },
  getRecords(params) { return request.get('/assessments/analysis-records/', { params }) },
  getRecord(id) { return request.get(`/assessments/analysis-records/${id}/`) },
  getRecordHistory(id) { return request.get(`/assessments/analysis-records/${id}/history/`) },
  updateRecord(id, data) { return request.patch(`/assessments/analysis-records/${id}/`, data) },
  getStatistics(params) { return request.get('/assessments/analysis-files/statistics/', { params }) }
}

export const leadershipAssessmentApi = {
  getFiles(params) { return request.get('/leadership-assessments/files/', { params }) },
  uploadFile(data) { return request.post('/leadership-assessments/files/upload-excel/', data, { headers: { 'Content-Type': 'multipart/form-data' } }) },
  updateFile(id, data) { return request.patch(`/leadership-assessments/files/${id}/`, data) },
  getRecords(params) { return request.get('/leadership-assessments/records/', { params }) },
  getRecord(id) { return request.get(`/leadership-assessments/records/${id}/`) },
  getRecordHistory(id) { return request.get(`/leadership-assessments/records/${id}/history/`) },
  updateRecord(id, data) { return request.patch(`/leadership-assessments/records/${id}/`, data) },
  getStatistics(params) { return request.get('/leadership-assessments/files/statistics/', { params }) }
}
