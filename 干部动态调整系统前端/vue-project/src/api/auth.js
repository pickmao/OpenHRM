import request from '@/utils/request'

/**
 * 用户登录
 */
export function login(data) {
  return request({
    url: '/auth/login/',
    method: 'post',
    data
  })
}

/**
 * 刷新Token
 */
export function refreshToken(refresh) {
  return request({
    url: '/auth/refresh/',
    method: 'post',
    data: { refresh }
  })
}

/**
 * 用户登出
 */
export function logout() {
  return request({
    url: '/auth/logout/',
    method: 'post'
  })
}

/**
 * 获取当前用户信息
 */
export function getUserInfo() {
  return request({
    url: '/auth/me/',
    method: 'get'
  })
}

/**
 * 修改密码
 */
export function changePassword(data) {
  return request({
    url: '/auth/change-password/',
    method: 'post',
    data
  })
}
