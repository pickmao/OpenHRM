import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/cadre/roster',
    name: 'PersonnelRoster',
    component: () => import('@/views/PersonnelRoster.vue'),
    meta: { requiresAuth: true }
  },
  // 组织架构管理
  {
    path: '/org',
    redirect: '/org/structure'
  },
  {
    path: '/org/structure',
    name: 'OrgStructure',
    component: () => import('@/views/org/Structure.vue'),
    meta: { requiresAuth: true, title: '组织架构' }
  },
  {
    path: '/org/department',
    name: 'OrgDepartment',
    component: () => import('@/views/org/Department.vue'),
    meta: { requiresAuth: true, title: '部门管理' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)

  if (requiresAuth && !userStore.isLoggedIn) {
    // 需要登录但未登录，跳转到登录页
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
  } else if (to.path === '/login' && userStore.isLoggedIn) {
    // 已登录用户访问登录页，跳转到首页
    next({ path: '/' })
  } else {
    next()
  }
})

export default router
