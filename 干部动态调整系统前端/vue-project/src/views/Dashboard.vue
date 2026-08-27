<template>
  <a-layout class="dashboard-layout">
    <!-- 侧边栏 -->
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
          <template #icon>
            <DashboardOutlined />
          </template>
          <span>系统首页</span>
        </a-menu-item>

        <a-sub-menu key="cadre">
          <template #icon>
            <UserOutlined />
          </template>
          <template #title>干部管理</template>
          <a-menu-item key="cadre-roster">花名册管理</a-menu-item>
        </a-sub-menu>

        <a-sub-menu key="allocation">
          <template #icon>
            <SwapOutlined />
          </template>
          <template #title>调配管理</template>
          <a-menu-item key="allocation-plan">调配计划</a-menu-item>
          <a-menu-item key="allocation-approval">调配审批</a-menu-item>
          <a-menu-item key="allocation-history">调配历史</a-menu-item>
        </a-sub-menu>

        <a-sub-menu key="forms" v-if="canViewForms">
          <template #icon><FileTextOutlined /></template>
          <template #title>表单下发与填报</template>
          <a-menu-item key="forms-tasks">我的待填报</a-menu-item>
          <a-menu-item v-if="canManageForms" key="forms-dispatch">表单下发</a-menu-item>
          <a-menu-item v-if="canManageForms" key="forms-progress">填报任务管理</a-menu-item>
        </a-sub-menu>

        <a-sub-menu key="assessment" v-if="canViewAssessments">
          <template #icon><FileTextOutlined /></template>
          <template #title>分析研判</template>
          <a-menu-item key="assessment-records">中层干部研判</a-menu-item>
          <a-menu-item key="assessment-analysis">干部研判分析</a-menu-item>
          <a-menu-item key="leadership-records">领导班子研判</a-menu-item>
          <a-menu-item key="leadership-analysis">班子研判分析</a-menu-item>
        </a-sub-menu>

        <a-sub-menu key="organization">
          <template #icon>
            <ApartmentOutlined />
          </template>
          <template #title>组织机构</template>
          <a-menu-item key="org-structure">组织架构</a-menu-item>
          <a-menu-item key="org-dept">部门管理</a-menu-item>
        </a-sub-menu>

        <a-sub-menu key="system" v-if="isAdmin">
          <template #icon>
            <SettingOutlined />
          </template>
          <template #title>系统管理</template>
          <a-menu-item key="system-user">用户管理</a-menu-item>
          <a-menu-item key="system-role">角色管理</a-menu-item>
        </a-sub-menu>
      </a-menu>
    </a-layout-sider>

    <a-layout :style="layoutStyle">
      <!-- 顶部导航栏 -->
      <a-layout-header class="header">
        <div class="header-left">
          <MenuUnfoldOutlined
            v-if="collapsed"
            class="trigger"
            @click="() => (collapsed = !collapsed)"
          />
          <MenuFoldOutlined
            v-else
            class="trigger"
            @click="() => (collapsed = !collapsed)"
          />
          <a-breadcrumb class="breadcrumb">
            <a-breadcrumb-item>首页</a-breadcrumb-item>
            <a-breadcrumb-item>{{ getCurrentPageName() }}</a-breadcrumb-item>
          </a-breadcrumb>
        </div>
        <div class="header-right">
          <a-space>
            <a-badge :count="notificationCount" :offset="[-5, 5]">
              <BellOutlined style="font-size: 18px; color: #fff;" />
            </a-badge>
            <a-dropdown>
              <a class="user-dropdown" @click.prevent>
                <a-avatar :size="32" style="margin-right: 8px;">
                  <template #icon>
                    <UserOutlined />
                  </template>
                </a-avatar>
                <span style="color: #fff;">{{ userStore.userInfo?.real_name || userStore.userInfo?.username }}</span>
                <DownOutlined style="margin-left: 5px; color: #fff;" />
              </a>
              <template #overlay>
                <a-menu>
                  <a-menu-item key="profile">
                    <UserOutlined />
                    个人中心
                  </a-menu-item>
                  <a-menu-item key="settings">
                    <SettingOutlined />
                    设置
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

      <!-- 主内容区 -->
      <a-layout-content class="content">
        <div class="content-wrapper">
          <!-- 统计卡片 -->
          <a-row :gutter="[16, 16]" class="stats-row">
            <a-col :xs="24" :sm="12" :md="6">
              <a-card>
                <a-statistic
                  title="干部总数"
                  :value="stats.totalCadres"
                  :value-style="{ color: '#1890ff' }"
                >
                  <template #prefix>
                    <UserOutlined />
                  </template>
                </a-statistic>
              </a-card>
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-card>
                <a-statistic
                  title="调配中"
                  :value="stats.inAllocation"
                  :value-style="{ color: '#52c41a' }"
                >
                  <template #prefix>
                    <SwapOutlined />
                  </template>
                </a-statistic>
              </a-card>
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-card>
                <a-statistic
                  title="风险预警"
                  :value="stats.riskWarnings"
                  :value-style="{ color: '#faad14' }"
                >
                  <template #prefix>
                    <AlertOutlined />
                  </template>
                </a-statistic>
              </a-card>
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-card>
                <a-statistic
                  title="待审批"
                  :value="stats.pendingApprovals"
                  :value-style="{ color: '#f5222d' }"
                >
                  <template #prefix>
                    <FileTextOutlined />
                  </template>
                </a-statistic>
              </a-card>
            </a-col>
          </a-row>

          <!-- 图表区域 -->
          <a-row :gutter="[16, 16]" class="charts-row">
            <a-col :xs="24" :lg="12">
              <a-card title="干部调配趋势" :bordered="false">
                <div class="chart-placeholder">
                  <LineChartOutlined style="font-size: 48px; color: #d9d9d9;" />
                  <p>图表区域 - 可集成 ECharts</p>
                </div>
              </a-card>
            </a-col>
            <a-col :xs="24" :lg="12">
              <a-card title="部门分布" :bordered="false">
                <div class="chart-placeholder">
                  <PieChartOutlined style="font-size: 48px; color: #d9d9d9;" />
                  <p>图表区域 - 可集成 ECharts</p>
                </div>
              </a-card>
            </a-col>
          </a-row>

          <!-- 快捷操作 -->
          <a-card title="快捷操作" class="quick-actions-card">
            <a-row :gutter="[16, 16]">
              <a-col :xs="12" :sm="8" :md="4" v-for="action in quickActions" :key="action.key">
                <div class="action-item" @click="handleQuickAction(action.key)">
                  <component :is="action.icon" style="font-size: 32px; color: #1890ff;" />
                  <p>{{ action.title }}</p>
                </div>
              </a-col>
            </a-row>
          </a-card>

          <!-- 最近活动 -->
          <a-card title="最近活动" class="recent-activities-card">
            <a-list
              :data-source="recentActivities"
              :split="false"
            >
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta>
                    <template #avatar>
                      <a-avatar :style="{ backgroundColor: item.color }">
                        <template #icon>
                          <component :is="item.icon" />
                        </template>
                      </a-avatar>
                    </template>
                    <template #title>
                      {{ item.title }}
                    </template>
                    <template #description>
                      {{ item.description }} - {{ item.time }}
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
            </a-list>
          </a-card>
        </div>
      </a-layout-content>

      <!-- 底部 -->
      <a-layout-footer class="footer">
        干部动态调配与智能预警系统 ©2024
      </a-layout-footer>
    </a-layout>
  </a-layout>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import {
  DashboardOutlined,
  UserOutlined,
  SwapOutlined,
  AlertOutlined,
  FileTextOutlined,
  ApartmentOutlined,
  SettingOutlined,
  MenuUnfoldOutlined,
  MenuFoldOutlined,
  BellOutlined,
  DownOutlined,
  LogoutOutlined,
  LineChartOutlined,
  PieChartOutlined,
  PlusOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined
} from '@ant-design/icons-vue'

const router = useRouter()
const userStore = useUserStore()

// 响应式数据
const collapsed = ref(false)
const selectedKeys = ref(['dashboard'])
const openKeys = ref(['cadre'])
const notificationCount = ref(5)

// 计算布局样式
const layoutStyle = computed(() => {
  return {
    marginLeft: collapsed.value ? '80px' : '200px',
    transition: 'margin-left 0.2s'
  }
})

// 统计数据
const stats = ref({
  totalCadres: 1234,
  inAllocation: 56,
  riskWarnings: 12,
  pendingApprovals: 8
})

// 快捷操作
const quickActions = ref([
  { key: 'roster', title: '花名册管理', icon: UserOutlined },
  { key: 'allocation', title: '发起调配', icon: SwapOutlined },
  { key: 'organization', title: '组织架构', icon: ApartmentOutlined },
  { key: 'form-tasks', title: '我的待填报', icon: FileTextOutlined }
])

// 最近活动
const recentActivities = ref([
  {
    title: '完成干部调配审批',
    description: '张三 从 人事处 调配到 财务处',
    time: '10分钟前',
    icon: CheckCircleOutlined,
    color: '#52c41a'
  },
  {
    title: '新增风险预警',
    description: '李四 在岗时间超期预警',
    time: '30分钟前',
    icon: AlertOutlined,
    color: '#faad14'
  },
  {
    title: '提交调配申请',
    description: '王五 从 办公室 申请调配到 宣传处',
    time: '1小时前',
    icon: FileTextOutlined,
    color: '#1890ff'
  },
  {
    title: '系统数据同步',
    description: '组织架构数据已更新',
    time: '2小时前',
    icon: SyncOutlined,
    color: '#722ed1'
  }
])

// 计算属性
const isAdmin = computed(() => {
  return userStore.userInfo?.is_superuser || userStore.hasPermission?.('accounts:user:manage')
})
const canViewForms = computed(() => userStore.hasPermission?.('forms:task:view') || userStore.hasPermission?.('forms:dispatch:manage') || userStore.userInfo?.is_superuser)
const canManageForms = computed(() => userStore.hasPermission?.('forms:dispatch:manage') || userStore.userInfo?.is_superuser)
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

// 获取当前页面名称
const getCurrentPageName = () => {
  const pageMap = {
    'dashboard': '系统首页',
    'cadre-roster': '花名册管理',
    'cadre-list': '干部列表',
    'cadre-profile': '干部档案',
    'cadre-analysis': '干部分析',
    'allocation-plan': '调配计划',
    'allocation-approval': '调配审批',
    'allocation-history': '调配历史',
    'risk-monitor': '风险监控',
    'risk-warning': '预警信息',
    'risk-report': '风险报告',
    'assessment-record': '考核记录',
    'assessment-analysis': '考核分析',
    'assessment-records': '中层干部研判',
    'leadership-records': '领导班子研判',
    'leadership-analysis': '班子研判分析',
    'forms-tasks': '我的待填报',
    'forms-dispatch': '表单下发',
    'forms-progress': '填报任务管理',
    'org-structure': '组织架构',
    'org-dept': '部门管理',
    'org-position': '岗位管理',
    'system-user': '用户管理',
    'system-role': '角色管理',
    'system-log': '审计日志'
  }
  return pageMap[selectedKeys.value[0]] || '系统首页'
}

// 快捷操作处理
const handleQuickAction = (action) => {
  const routes = {
    roster: '/cadre/roster',
    allocation: '/allocation/plan',
    organization: '/org/structure',
    'form-tasks': '/forms/tasks'
  }
  if (routes[action]) router.push(routes[action])
}

// 菜单选择处理
const handleMenuSelect = ({ key }) => {
  const routeMap = {
    'dashboard': '/dashboard',
    'cadre-roster': '/cadre/roster',
    'allocation-plan': '/allocation/plan',
    'allocation-approval': '/allocation/approval',
    'allocation-history': '/allocation/history',
    'forms-tasks': '/forms/tasks',
    'forms-dispatch': '/forms/dispatch',
    'forms-progress': '/forms/progress',
    'assessment-records': '/assessments/records',
    'assessment-analysis': '/assessments/analysis',
    'leadership-records': '/leadership-assessments/records',
    'leadership-analysis': '/leadership-assessments/analysis',
    'org-structure': '/org/structure',
    'org-dept': '/org/department',
    'system-user': '/admin/users/roles',
    'system-role': '/admin/roles',
  }

  const route = routeMap[key]
  if (route && route !== router.currentRoute.value.path) {
    router.push(route)
  }
}

// 退出登录
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
.dashboard-layout {
  min-height: 100vh;
  display: flex;
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

.breadcrumb :deep(.ant-breadcrumb-link) {
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
  margin: 24px;
  min-height: calc(100vh - 64px - 70px - 48px);
}

.content-wrapper {
  padding: 24px;
  background: #fff;
  border-radius: 4px;
}

.stats-row {
  margin-bottom: 16px;
}

.charts-row {
  margin-bottom: 16px;
}

.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #999;
}

.quick-actions-card {
  margin-bottom: 16px;
}

.action-item {
  text-align: center;
  padding: 20px 10px;
  cursor: pointer;
  transition: all 0.3s;
  border-radius: 4px;
}

.action-item:hover {
  background: #f5f5f5;
}

.action-item p {
  margin: 10px 0 0 0;
  color: #333;
  font-size: 14px;
}

.recent-activities-card {
  margin-bottom: 0;
}

.footer {
  text-align: center;
  background: #f0f2f5;
}

/* 响应式布局 */
@media (max-width: 768px) {
  .header {
    padding: 0 16px;
  }

  .content {
    margin: 16px;
  }

  .content-wrapper {
    padding: 16px;
  }
}
</style>
