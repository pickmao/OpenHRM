import request from '@/utils/request'

export const overallReviewApi = {
  search(name) { return request.get('/overall-reviews/search/', { params: { name } }) },
  preview(id) { return request.get(`/overall-reviews/${id}/`) },
  generate(id, digest) {
    return request.post(`/overall-reviews/${id}/generate/`,
      { digest, confirm_external_transfer: true }, { timeout: 110000 })
  }
}
