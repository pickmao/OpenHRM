<template>
  <a-layout class="main-layout">
    <a-layout-sider
      v-model:collapsed="collapsed"
      :trigger="null"
      collapsible
      :width="200"
      :style="{ overflow: 'auto', height: '100vh', position: 'fixed', left: 0, top: 0, bottom: 0 }"
    >
      <div class="logo">
        <h2 v-if="!collapsed">干部管理系统</h2>
        <h2 v-else>干部</h2>
      </div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        v-model:openKeys="openKeys"
        mode="inline"
        theme="dark"
        :inline-collapsed="collapsed"
        @select="handleMenuSelect"
      >
        <a-menu-item key="dashboard">
          <template #icon><DashboardOutlined /></template>
          <span>系统首页</span>
        </a-menu-item>

        <a-sub-menu key="cadre">
          <template #icon><UserOutlined /></template>
          <template #title>干部管理</template>
          <a-menu-item key="cadre-roster">花名册管理</a-menu-item>
        </a-sub-menu>

        <a-sub-menu key="knowing-people">
          <template #icon><AuditOutlined /></template>
          <template #title>知事识人</template>
          <a-menu-item v-if="canManageKnowingPeople" key="knowing-dispatch">任务下发</a-menu-item>
          <a-menu-item v-if="canFillKnowingPeople" key="knowing-tasks">我的填报</a-menu-item>
          <a-menu-item v-if="canViewKnowingProgress" key="knowing-progress">填报进度</a-menu-item>
          <a-menu-item key="work-records">知事识人纪实</a-menu-item>
        </a-sub-menu>

        <a-sub-menu key="allocation">
          <template #icon><SwapOutlined /></template>
          <template #title>调配管理</template>
          <a-menu-item key="allocation-plan">部门调配</a-menu-item>
          <a-menu-item key="allocation-history">调配历史</a-menu-item>
        </a-sub-menu>

        <a-sub-menu key="forms" v-if="canViewForms">
          <template #icon><FileTextOutlined /></template>
          <template #title>表单下发与填报</template>
          <a-menu-item key="forms-tasks">我的待填报</a-menu-item>
          <a-menu-item v-if="canManageForms" key="forms-dispatch">表单下发</a-menu-item>
          <a-menu-item v-if="canManageForms" key="forms-progress">填报任务管理</a-menu-item>
        </a-sub-menu>

        <a-sub-menu key="anonymous-evaluations" v-if="canViewEvaluations">
          <template #icon><FileTextOutlined /></template>
          <template #title>匿名民主测评</template>
          <a-menu-item v-if="canSubmitEvaluations" key="evaluation-tasks">我的匿名评价</a-menu-item>
          <a-menu-item v-if="canManageEvaluations" key="evaluation-manage">评价活动管理</a-menu-item>
          <a-menu-item v-if="canViewEvaluationResults" key="evaluation-results">评价结果分析</a-menu-item>
        </a-sub-menu>

        <a-sub-menu key="recommendations" v-if="canViewRecommendations">
          <template #icon><FileTextOutlined /></template>
          <template #title>优秀干部推荐</template>
          <a-menu-item v-if="canSubmitRecommendations" key="recommend-tasks">我的推荐表</a-menu-item>
          <a-menu-item v-if="canManageRecommendations" key="recommend-manage">推荐活动下发</a-menu-item>
          <a-menu-item v-if="canViewRecommendationStats" key="recommend-stats">推荐结果统计</a-menu-item>
        </a-sub-menu>

        <a-sub-menu key="assessment" v-if="canViewAssessments">
          <template #icon><FileTextOutlined /></template>
          <template #title>分析研判</template>
          <a-menu-item key="assessment-records">中层干部研判</a-menu-item>
          <a-menu-item key="assessment-analysis">干部研判分析</a-menu-item>
          <a-menu-item key="leadership-records">领导班子研判</a-menu-item>
          <a-menu-item key="leadership-analysis">班子研判分析</a-menu-item>
        </a-sub-menu>

        <a-sub-menu key="rewards" v-if="canViewRewards">
          <template #icon><FileTextOutlined /></template>
          <template #title>奖励管理</template>
          <a-menu-item key="reward-summary">个人及集体奖励汇总</a-menu-item>
        </a-sub-menu>

        <a-sub-menu key="organization">
          <template #icon><ApartmentOutlined /></template>
          <template #title>组织机构</template>
          <a-menu-item key="org-structure">组织架构</a-menu-item>
          <a-menu-item key="org-branch">支部管理</a-menu-item>
          <a-menu-item key="org-dept">部门管理</a-menu-item>
        </a-sub-menu>

        <a-sub-menu key="system" v-if="isAdmin">
          <template #icon><SettingOutlined /></template>
          <template #title>系统管理</template>
          <a-menu-item key="system-user">用户管理</a-menu-item>
          <a-menu-item key="system-role">角色管理</a-menu-item>
        </a-sub-menu>
      </a-menu>
    </a-layout-sider>

    <a-layout :style="layoutStyle">
      <a-layout-header class="header">
        <div class="header-left">
          <MenuUnfoldOutlined v-if="collapsed" class="trigger" @click="collapsed = !collapsed" />
          <MenuFoldOutlined v-else class="trigger" @click="collapsed = !collapsed" />
          <a-breadcrumb class="breadcrumb">
            <a-breadcrumb-item>
              <router-link to="/dashboard">首页</router-link>
            </a-breadcrumb-item>
            <a-breadcrumb-item v-if="currentPageName !== '系统首页'">
              {{ currentPageName }}
            </a-breadcrumb-item>
          </a-breadcrumb>
        </div>
        <div class="header-right">
          <a-space>
            <a-tooltip title="通知中心尚未接入">
              <BellOutlined style="font-size: 18px; color: rgba(255,255,255,0.65); cursor: not-allowed;" />
            </a-tooltip>
            <a-dropdown>
              <a class="user-dropdown" @click.prevent>
                <a-avatar :size="32" style="margin-right: 8px;">
                  <template #icon><UserOutlined /></template>
                </a-avatar>
                <span style="color: #fff;">{{ userStore.userInfo?.real_name || userStore.userInfo?.username }}</span>
                <DownOutlined style="margin-left: 5px; color: #fff;" />
              </a>
              <template #overlay>
                <a-menu>
                  <a-menu-item key="profile" disabled>
                    <UserOutlined />
                    个人中心（未接入）
                  </a-menu-item>
                  <a-menu-item key="settings" disabled>
                    <SettingOutlined />
                    设置（未接入）
                  </a-menu-item>
                  <a-menu-divider />
                  <a-menu-item key="logout" @click="handleLogout">
                    <LogoutOutlined />
                    退出登录
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </a-space>
        </div>
      </a-layout-header>

      <a-layout-content class="content">
        <router-view />
      </a-layout-content>

      <a-layout-footer class="footer">
        干部动态调配与智能预警系统 ©2024
      </a-layout-footer>
    </a-layout>
  </a-layout>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import {
  DashboardOutlined,
  UserOutlined,
  SwapOutlined,
  FileTextOutlined,
  ApartmentOutlined,
  SettingOutlined,
  MenuUnfoldOutlined,
  MenuFoldOutlined,
  BellOutlined,
  DownOutlined,
  LogoutOutlined,
  AuditOutlined
} from '@ant-design/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const collapsed = ref(false)
const selectedKeys = ref(['dashboard'])
const openKeys = ref(['cadre'])

const routeMenuMap = {
  '/dashboard': { key: 'dashboard', open: [] },
  '/': { key: 'dashboard', open: [] },
  '/cadre/roster': { key: 'cadre-roster', open: ['cadre'] },
  '/knowing-people/dispatch': { key: 'knowing-dispatch', open: ['knowing-people'] },
  '/knowing-people/tasks': { key: 'knowing-tasks', open: ['knowing-people'] },
  '/knowing-people/progress': { key: 'knowing-progress', open: ['knowing-people'] },
  '/inspections/records': { key: 'work-records', open: ['knowing-people'] },
  '/allocation/plan': { key: 'allocation-plan', open: ['allocation'] },
  '/allocation/history': { key: 'allocation-history', open: ['allocation'] },
  '/forms/tasks': { key: 'forms-tasks', open: ['forms'] },
  '/forms/dispatch': { key: 'forms-dispatch', open: ['forms'] },
  '/forms/progress': { key: 'forms-progress', open: ['forms'] },
  '/evaluations/tasks': { key: 'evaluation-tasks', open: ['anonymous-evaluations'] },
  '/evaluations/manage': { key: 'evaluation-manage', open: ['anonymous-evaluations'] },
  '/evaluations/results': { key: 'evaluation-results', open: ['anonymous-evaluations'] },
  '/recommendations/tasks': { key: 'recommend-tasks', open: ['recommendations'] },
  '/recommendations/manage': { key: 'recommend-manage', open: ['recommendations'] },
  '/recommendations/stats': { key: 'recommend-stats', open: ['recommendations'] },
  '/assessments/records': { key: 'assessment-records', open: ['assessment'] },
  '/assessments/analysis': { key: 'assessment-analysis', open: ['assessment'] },
  '/leadership-assessments/records': { key: 'leadership-records', open: ['assessment'] },
  '/leadership-assessments/analysis': { key: 'leadership-analysis', open: ['assessment'] },
  '/rewards/summary': { key: 'reward-summary', open: ['rewards'] },
  '/org/structure': { key: 'org-structure', open: ['organization'] },
  '/org/branch': { key: 'org-branch', open: ['organization'] },
  '/org/department': { key: 'org-dept', open: ['organization'] },
  '/admin/users/roles': { key: 'system-user', open: ['system'] },
  '/admin/roles': { key: 'system-role', open: ['system'] },
  '/admin/roles/create': { key: 'system-role', open: ['system'] },
  '/admin/permissions': { key: 'system-role', open: ['system'] }
}

const pageNameMap = {
  dashboard: '系统首页',
  'cadre-roster': '花名册管理',
  'knowing-dispatch': '任务下发',
  'knowing-tasks': '我的填报',
  'knowing-progress': '填报进度',
  'work-records': '知事识人纪实',
  'allocation-plan': '部门调配',
  'allocation-history': '调配历史',
  'forms-tasks': '我的待填报',
  'forms-dispatch': '表单下发',
  'forms-progress': '填报任务管理',
  'evaluation-tasks': '我的匿名评价',
  'evaluation-manage': '评价活动管理',
  'evaluation-results': '评价结果分析',
  'recommend-tasks': '我的推荐表',
  'recommend-manage': '推荐活动下发',
  'recommend-stats': '推荐结果统计',
  'assessment-records': '中层干部研判',
  'assessment-analysis': '干部研判分析',
  'leadership-records': '领导班子研判',
  'leadership-analysis': '班子研判分析',
  'reward-summary': '个人及集体奖励汇总',
  'org-structure': '组织架构',
  'org-branch': '支部管理',
  'org-dept': '部门管理',
  'system-user': '用户管理',
  'system-role': '角色管理'
}

const syncMenuFromRoute = () => {
  const menuKey = route.meta?.menuKey
  if (menuKey) {
    selectedKeys.value = [menuKey]
    const openGroup = Object.entries(routeMenuMap).find(([, value]) => value.key === menuKey)?.[1]?.open
    if (openGroup?.length) {
      openKeys.value = Array.from(new Set([...openKeys.value, ...openGroup]))
    }
    return
  }

  const matched = routeMenuMap[route.path]
  if (matched) {
    selectedKeys.value = [matched.key]
    if (matched.open?.length) {
      openKeys.value = Array.from(new Set([...openKeys.value, ...matched.open]))
    }
  }
}

watch(() => route.fullPath, () => syncMenuFromRoute(), { immediate: true })

const layoutStyle = computed(() => ({
  marginLeft: collapsed.value ? '80px' : '200px',
  transition: 'margin-left 0.2s',
  minHeight: '100vh'
}))

const currentPageName = computed(() => {
  return route.meta?.title || pageNameMap[selectedKeys.value[0]] || '系统首页'
})

const isAdmin = computed(() => userStore.userInfo?.is_superuser || userStore.hasPermission?.('accounts:user:manage'))
const canViewForms = computed(() => userStore.hasPermission?.('forms:task:view') || userStore.hasPermission?.('forms:dispatch:manage') || userStore.userInfo?.is_superuser)
const canManageForms = computed(() => userStore.hasPermission?.('forms:dispatch:manage') || userStore.userInfo?.is_superuser)
const canSubmitEvaluations = computed(() => userStore.hasPermission?.('anonymous_evaluations:task:view') || userStore.hasPermission?.('anonymous_evaluations:task:submit') || userStore.userInfo?.is_superuser)
const canManageEvaluations = computed(() => userStore.hasPermission?.('anonymous_evaluations:campaign:manage') || userStore.userInfo?.is_superuser)
const canViewEvaluationResults = computed(() => userStore.hasPermission?.('anonymous_evaluations:result:view') || userStore.userInfo?.is_superuser)
const canViewEvaluations = computed(() => canSubmitEvaluations.value || canManageEvaluations.value || canViewEvaluationResults.value)
const canSubmitRecommendations = computed(() => userStore.hasPermission?.('cadre_recommendations:task:view') || userStore.hasPermission?.('cadre_recommendations:task:submit') || userStore.userInfo?.is_superuser)
const canManageRecommendations = computed(() => userStore.hasPermission?.('cadre_recommendations:campaign:manage') || userStore.userInfo?.is_superuser)
const canViewRecommendationStats = computed(() => userStore.hasPermission?.('cadre_recommendations:result:view') || userStore.hasPermission?.('cadre_recommendations:campaign:manage') || userStore.userInfo?.is_superuser)
const canViewRecommendations = computed(() => canSubmitRecommendations.value || canManageRecommendations.value || canViewRecommendationStats.value)
const canViewAssessments = computed(() => {
  const permissions = [
    'assessments:view', 'assessments:manage',
    'assessments:record:view', 'assessments:record:manage',
    'assessments:file:view', 'assessments:file:manage',
    'leadership:record:view', 'leadership:record:manage',
    'leadership:file:view', 'leadership:file:manage'
  ]
  return userStore.userInfo?.is_superuser || permissions.some(permission => userStore.hasPermission?.(permission))
})
const canFillKnowingPeople = computed(() => userStore.hasPermission?.('knowing_people:task:view') || userStore.hasPermission?.('knowing_people:task:submit') || userStore.userInfo?.is_superuser)
const canManageKnowingPeople = computed(() => userStore.hasPermission?.('knowing_people:campaign:manage') || userStore.userInfo?.is_superuser)
const canViewKnowingProgress = computed(() => userStore.hasPermission?.('knowing_people:result:view') || userStore.hasPermission?.('knowing_people:campaign:manage') || userStore.userInfo?.is_superuser)
const canViewRewards = computed(() => userStore.userInfo?.is_superuser || ['rewards:view', 'rewards:manage', 'rewards:record:view', 'rewards:record:manage', 'rewards:file:view', 'rewards:file:manage'].some(permission => userStore.hasPermission?.(permission)))

const routeMap = {
  dashboard: '/dashboard',
  'cadre-roster': '/cadre/roster',
  'knowing-dispatch': '/knowing-people/dispatch',
  'knowing-tasks': '/knowing-people/tasks',
  'knowing-progress': '/knowing-people/progress',
  'work-records': '/inspections/records',
  'allocation-plan': '/allocation/plan',
  'allocation-history': '/allocation/history',
  'forms-tasks': '/forms/tasks',
  'forms-dispatch': '/forms/dispatch',
  'forms-progress': '/forms/progress',
  'evaluation-tasks': '/evaluations/tasks',
  'evaluation-manage': '/evaluations/manage',
  'evaluation-results': '/evaluations/results',
  'recommend-tasks': '/recommendations/tasks',
  'recommend-manage': '/recommendations/manage',
  'recommend-stats': '/recommendations/stats',
  'assessment-records': '/assessments/records',
  'assessment-analysis': '/assessments/analysis',
  'leadership-records': '/leadership-assessments/records',
  'leadership-analysis': '/leadership-assessments/analysis',
  'reward-summary': '/rewards/summary',
  'org-structure': '/org/structure',
  'org-branch': '/org/branch',
  'org-dept': '/org/department',
  'system-user': '/admin/users/roles',
  'system-role': '/admin/roles'
}

const handleMenuSelect = ({ key }) => {
  const target = routeMap[key]
  if (target && target !== route.path) {
    router.push(target)
  }
}

const handleLogout = () => {
  Modal.confirm({
    title: '确认退出',
    content: '您确定要退出登录吗？',
    okText: '确定',
    cancelText: '取消',
    onOk: async () => {
      await userStore.logout()
      message.success('已退出登录')
      router.push('/login')
    }
  })
}
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  margin: 16px;
  border-radius: 6px;
}

.logo h2 {
  color: #fff;
  margin: 0;
  font-size: 18px;
  white-space: nowrap;
}

.header {
  background: #001529;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
}

.trigger {
  font-size: 18px;
  line-height: 64px;
  cursor: pointer;
  transition: color 0.3s;
  color: #fff;
  margin-right: 16px;
}

.trigger:hover {
  color: #1890ff;
}

.breadcrumb {
  margin-left: 16px;
}

.breadcrumb :deep(.ant-breadcrumb-link),
.breadcrumb :deep(a) {
  color: rgba(255, 255, 255, 0.85);
}

.header-right {
  display: flex;
  align-items: center;
}

.user-dropdown {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.content {
  margin: 0;
  min-height: calc(100vh - 64px - 70px);
  background: #f0f2f5;
}

.footer {
  text-align: center;
  background: #f0f2f5;
}

@media (max-width: 768px) {
  .header {
    padding: 0 16px;
  }
}
</style>
