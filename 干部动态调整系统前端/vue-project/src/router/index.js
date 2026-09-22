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
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { requiresAuth: true, title: '系统首页', menuKey: 'dashboard' }
      },
      {
        path: 'cadre/roster',
        name: 'PersonnelRoster',
        component: () => import('@/views/PersonnelRoster.vue'),
        meta: { requiresAuth: true, title: '花名册管理', menuKey: 'cadre-roster' }
      },
      {
        path: 'knowing-people/dispatch',
        name: 'KnowingPeopleDispatch',
        component: () => import('@/views/knowing-people/Dispatch.vue'),
        meta: { requiresAuth: true, title: '知事识人任务下发', menuKey: 'knowing-dispatch' }
      },
      {
        path: 'knowing-people/tasks',
        name: 'KnowingPeopleTasks',
        component: () => import('@/views/knowing-people/MyTasks.vue'),
        meta: { requiresAuth: true, title: '我的填报', menuKey: 'knowing-tasks' }
      },
      {
        path: 'knowing-people/tasks/:id',
        name: 'KnowingPeopleFill',
        component: () => import('@/views/knowing-people/Fill.vue'),
        meta: { requiresAuth: true, title: '填写知事识人表单', menuKey: 'knowing-tasks' }
      },
      {
        path: 'knowing-people/progress',
        name: 'KnowingPeopleProgress',
        component: () => import('@/views/knowing-people/Progress.vue'),
        meta: { requiresAuth: true, title: '知事识人填报进度', menuKey: 'knowing-progress' }
      },
      {
        path: 'inspections/records',
        name: 'WorkRecords',
        component: () => import('@/views/WorkRecords.vue'),
        meta: { requiresAuth: true, title: '知事识人纪实', menuKey: 'work-records' }
      },
      {
        path: 'allocation/plan',
        name: 'AllocationPlan',
        component: () => import('@/views/allocation/AllocationPlan.vue'),
        meta: { requiresAuth: true, title: '部门调配', menuKey: 'allocation-plan' }
      },
      {
        path: 'allocation/approval',
        redirect: '/allocation/plan'
      },
      {
        path: 'allocation/history',
        name: 'AllocationHistory',
        component: () => import('@/views/allocation/AllocationHistory.vue'),
        meta: { requiresAuth: true, title: '调配历史', menuKey: 'allocation-history' }
      },
      {
        path: 'admin',
        redirect: '/admin/roles'
      },
      {
        path: 'admin/roles',
        name: 'AdminRoles',
        component: () => import('@/views/admin/RoleList.vue'),
        meta: { requiresAuth: true, title: '角色管理', menuKey: 'system-role' }
      },
      {
        path: 'admin/roles/create',
        name: 'AdminRoleCreate',
        component: () => import('@/views/admin/RoleCreate.vue'),
        meta: { requiresAuth: true, title: '新建角色', menuKey: 'system-role' }
      },
      {
        path: 'admin/roles/:id',
        name: 'AdminRoleDetail',
        component: () => import('@/views/admin/RoleDetail.vue'),
        meta: { requiresAuth: true, title: '配置角色权限', menuKey: 'system-role' }
      },
      {
        path: 'admin/permissions',
        name: 'AdminPermissions',
        component: () => import('@/views/admin/PermissionCatalog.vue'),
        meta: { requiresAuth: true, title: '权限目录', menuKey: 'system-role' }
      },
      {
        path: 'admin/users/roles',
        name: 'AdminUserRoles',
        component: () => import('@/views/admin/UserRoles.vue'),
        meta: { requiresAuth: true, title: '用户角色分配', menuKey: 'system-user' }
      },
      {
        path: 'forms/dispatch',
        name: 'FormDispatch',
        component: () => import('@/views/forms/FormDispatch.vue'),
        meta: { requiresAuth: true, title: '表单下发', menuKey: 'forms-dispatch' }
      },
      {
        path: 'forms/tasks',
        name: 'FormTasks',
        component: () => import('@/views/forms/FormTasks.vue'),
        meta: { requiresAuth: true, title: '我的待填报', menuKey: 'forms-tasks' }
      },
      {
        path: 'forms/progress',
        name: 'FormProgress',
        component: () => import('@/views/forms/FormProgress.vue'),
        meta: { requiresAuth: true, title: '填报任务管理', menuKey: 'forms-progress' }
      },
      {
        path: 'forms/tasks/:id/edit',
        name: 'FormOnlyOfficeTask',
        component: () => import('@/views/forms/FormOnlyOfficeTask.vue'),
        meta: { requiresAuth: true, title: '在线填写', menuKey: 'forms-tasks' }
      },
      {
        path: 'forms/tasks/:id/view',
        name: 'FormOnlyOfficeTaskView',
        component: () => import('@/views/forms/FormOnlyOfficeTaskView.vue'),
        meta: { requiresAuth: true, title: '查看填报结果', menuKey: 'forms-tasks' }
      },
      {
        path: 'evaluations/tasks',
        name: 'EvaluationTasks',
        component: () => import('@/views/evaluations/EvaluationTasks.vue'),
        meta: { requiresAuth: true, title: '我的匿名评价', menuKey: 'evaluation-tasks' }
      },
      {
        path: 'evaluations/manage',
        name: 'EvaluationManage',
        component: () => import('@/views/evaluations/EvaluationManage.vue'),
        meta: { requiresAuth: true, title: '匿名评价活动管理', menuKey: 'evaluation-manage' }
      },
      {
        path: 'evaluations/results',
        name: 'EvaluationResults',
        component: () => import('@/views/evaluations/EvaluationResults.vue'),
        meta: { requiresAuth: true, title: '匿名评价结果分析', menuKey: 'evaluation-results' }
      },
      {
        path: 'assessments/records',
        name: 'AssessmentRecords',
        component: () => import('@/views/AssessmentRecords.vue'),
        meta: { requiresAuth: true, title: '中层干部研判', menuKey: 'assessment-records' }
      },
      {
        path: 'assessments/analysis',
        name: 'AssessmentAnalysis',
        component: () => import('@/views/AssessmentAnalysis.vue'),
        meta: { requiresAuth: true, title: '中层干部研判分析', menuKey: 'assessment-analysis' }
      },
      {
        path: 'leadership-assessments/records',
        name: 'LeadershipRecords',
        component: () => import('@/views/LeadershipRecords.vue'),
        meta: { requiresAuth: true, title: '领导班子研判', menuKey: 'leadership-records' }
      },
      {
        path: 'leadership-assessments/analysis',
        name: 'LeadershipAnalysis',
        component: () => import('@/views/LeadershipAnalysis.vue'),
        meta: { requiresAuth: true, title: '领导班子研判分析', menuKey: 'leadership-analysis' }
      },
      {
        path: 'rewards/summary',
        name: 'RewardSummary',
        component: () => import('@/views/RewardSummary.vue'),
        meta: { requiresAuth: true, title: '个人及集体奖励汇总', menuKey: 'reward-summary' }
      },
      {
        path: 'org',
        redirect: '/org/structure'
      },
      {
        path: 'org/structure',
        name: 'OrgStructure',
        component: () => import('@/views/org/Structure.vue'),
        meta: { requiresAuth: true, title: '组织架构', menuKey: 'org-structure' }
      },
      {
        path: 'org/department',
        name: 'OrgDepartment',
        component: () => import('@/views/org/Department.vue'),
        meta: { requiresAuth: true, title: '部门管理', menuKey: 'org-dept' }
      },
      {
        path: 'org/branch',
        name: 'OrgBranch',
        component: () => import('@/views/org/Branch.vue'),
        meta: { requiresAuth: true, title: '支部管理', menuKey: 'org-branch' }
      },
      {
        path: 'recommendations/tasks',
        name: 'RecommendTasks',
        component: () => import('@/views/recommendations/RecommendTasks.vue'),
        meta: { requiresAuth: true, title: '我的推荐表', menuKey: 'recommend-tasks' }
      },
      {
        path: 'recommendations/tasks/:id',
        name: 'RecommendFill',
        component: () => import('@/views/recommendations/RecommendFill.vue'),
        meta: { requiresAuth: true, title: '填写推荐表', menuKey: 'recommend-tasks' }
      },
      {
        path: 'recommendations/manage',
        name: 'RecommendManage',
        component: () => import('@/views/recommendations/RecommendManage.vue'),
        meta: { requiresAuth: true, title: '优秀干部推荐下发', menuKey: 'recommend-manage' }
      },
      {
        path: 'recommendations/stats',
        name: 'RecommendStats',
        component: () => import('@/views/recommendations/RecommendStats.vue'),
        meta: { requiresAuth: true, title: '优秀干部推荐统计', menuKey: 'recommend-stats' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)

  if (requiresAuth && !userStore.isLoggedIn) {
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
  } else if (to.path === '/login' && userStore.isLoggedIn) {
    next({ path: '/dashboard' })
  } else {
    next()
  }
})

export default router
