import { defineStore } from 'pinia'
import { login as loginApi, logout as logoutApi, getUserInfo } from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    refreshToken: localStorage.getItem('refresh_token') || '',
    userInfo: JSON.parse(localStorage.getItem('user_info') || 'null'),
    permissions: JSON.parse(localStorage.getItem('permissions') || '[]')
  }),

  getters: {
    // 是否已登录
    isLoggedIn: (state) => !!state.token,

    // 获取用户真实姓名
    userName: (state) => state.userInfo?.real_name || state.userInfo?.username || '',

    // 获取用户角色
    userRole: (state) => state.userInfo?.role || '',

    // 检查是否有某个权限
    hasPermission: (state) => (permission) => {
      return state.permissions.includes(permission)
    },

    // 是否是管理员
    isAdmin: (state) => state.userInfo?.is_superuser || false
  },

  actions: {
    // 登录
    async login(credentials) {
      try {
        const response = await loginApi(credentials)

        // 保存token
        this.token = response.access
        this.refreshToken = response.refresh
        this.userInfo = response.user
        this.permissions = response.permissions || []

        // 持久化到localStorage
        localStorage.setItem('access_token', response.access)
        localStorage.setItem('refresh_token', response.refresh)
        localStorage.setItem('user_info', JSON.stringify(response.user))
        localStorage.setItem('permissions', JSON.stringify(response.permissions || []))

        return { success: true }
      } catch (error) {
        console.error('登录失败:', error)
        return {
          success: false,
          message: error.response?.data?.detail || '登录失败，请检查用户名和密码'
        }
      }
    },

    // 登出
    async logout() {
      try {
        await logoutApi()
      } catch (error) {
        console.error('登出请求失败:', error)
      } finally {
        // 清除本地数据
        this.token = ''
        this.refreshToken = ''
        this.userInfo = null
        this.permissions = []

        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user_info')
        localStorage.removeItem('permissions')
      }
    },

    // 获取用户信息
    async fetchUserInfo() {
      try {
        const response = await getUserInfo()
        this.userInfo = response
        this.permissions = response.permissions || []

        localStorage.setItem('user_info', JSON.stringify(response))
        localStorage.setItem('permissions', JSON.stringify(response.permissions || []))

        return response
      } catch (error) {
        console.error('获取用户信息失败:', error)
        throw error
      }
    },

    // 更新用户信息
    updateUserInfo(userInfo) {
      this.userInfo = { ...this.userInfo, ...userInfo }
      localStorage.setItem('user_info', JSON.stringify(this.userInfo))
    }
  }
})
