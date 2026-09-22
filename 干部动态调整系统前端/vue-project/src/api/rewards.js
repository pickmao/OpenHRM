import request from '@/utils/request'

export const rewardApi = {
  getFiles(params) {
    return request({ url: '/rewards/reward-files/', method: 'get', params })
  },
  uploadFile(data) {
    return request({ url: '/rewards/reward-files/upload-excel/', method: 'post', data })
  },
  getRecords(params) {
    return request({ url: '/rewards/reward-records/', method: 'get', params })
  },
  getRecord(id) {
    return request({ url: `/rewards/reward-records/${id}/`, method: 'get' })
  },
  createRecord(data) {
    return request({ url: '/rewards/reward-records/', method: 'post', data })
  },
  updateRecord(id, data) {
    return request({ url: `/rewards/reward-records/${id}/`, method: 'patch', data })
  },
  deleteRecord(id) {
    return request({ url: `/rewards/reward-records/${id}/`, method: 'delete' })
  },
  getStatistics(params) {
    return request({ url: '/rewards/reward-records/statistics/', method: 'get', params })
  },
}
