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
  {
    path: '/allocation/plan',
    name: 'AllocationPlan',
    component: () => import('@/views/allocation/AllocationPlan.vue'),
    meta: { requiresAuth: true, title: '部门调配' }
  },
  {
    path: '/allocation/approval',
    name: 'AllocationApproval',
    component: () => import('@/views/allocation/AllocationApproval.vue'),
    meta: { requiresAuth: true, title: '调配审批' }
  },
  {
    path: '/allocation/history',
    name: 'AllocationHistory',
    component: () => import('@/views/allocation/AllocationHistory.vue'),
    meta: { requiresAuth: true, title: '调配历史' }
  },
  {
    path: '/admin',
    redirect: '/admin/roles'
  },
  {
    path: '/admin/roles',
    name: 'AdminRoles',
    component: () => import('@/views/admin/RoleList.vue'),
    meta: { requiresAuth: true, title: '角色管理' }
  },
  {
    path: '/admin/roles/create',
    name: 'AdminRoleCreate',
    component: () => import('@/views/admin/RoleCreate.vue'),
    meta: { requiresAuth: true, title: '新建角色' }
  },
  {
    path: '/admin/roles/:id',
    name: 'AdminRoleDetail',
    component: () => import('@/views/admin/RoleDetail.vue'),
    meta: { requiresAuth: true, title: '配置角色权限' }
  },
  {
    path: '/admin/permissions',
    name: 'AdminPermissions',
    component: () => import('@/views/admin/PermissionCatalog.vue'),
    meta: { requiresAuth: true, title: '权限目录' }
  },
  {
    path: '/admin/users/roles',
    name: 'AdminUserRoles',
    component: () => import('@/views/admin/UserRoles.vue'),
    meta: { requiresAuth: true, title: '用户角色分配' }
  },
  {
    path: '/forms/dispatch',
    name: 'FormDispatch',
    component: () => import('@/views/forms/FormDispatch.vue'),
    meta: { requiresAuth: true, title: '表单下发' }
  },
  {
    path: '/forms/tasks',
    name: 'FormTasks',
    component: () => import('@/views/forms/FormTasks.vue'),
    meta: { requiresAuth: true, title: '我的待填报' }
  },
  {
    path: '/forms/progress',
    name: 'FormProgress',
    component: () => import('@/views/forms/FormProgress.vue'),
    meta: { requiresAuth: true, title: '填报任务管理' }
  },
  {
    path: '/forms/tasks/:id/edit',
    name: 'FormOnlyOfficeTask',
    component: () => import('@/views/forms/FormOnlyOfficeTask.vue'),
    meta: { requiresAuth: true, title: '在线填写' }
  },
  {
    path: '/forms/tasks/:id/view',
    name: 'FormOnlyOfficeTaskView',
    component: () => import('@/views/forms/FormOnlyOfficeTaskView.vue'),
    meta: { requiresAuth: true, title: '查看填报结果' }
  },
  {
    path: '/assessments/records',
    name: 'AssessmentRecords',
    component: () => import('@/views/AssessmentRecords.vue'),
    meta: { requiresAuth: true, title: '中层干部研判' }
  },
  {
    path: '/assessments/analysis',
    name: 'AssessmentAnalysis',
    component: () => import('@/views/AssessmentAnalysis.vue'),
    meta: { requiresAuth: true, title: '中层干部研判分析' }
  },
  {
    path: '/leadership-assessments/records',
    name: 'LeadershipRecords',
    component: () => import('@/views/LeadershipRecords.vue'),
    meta: { requiresAuth: true, title: '领导班子研判' }
  },
  {
    path: '/leadership-assessments/analysis',
    name: 'LeadershipAnalysis',
    component: () => import('@/views/LeadershipAnalysis.vue'),
    meta: { requiresAuth: true, title: '领导班子研判分析' }
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
