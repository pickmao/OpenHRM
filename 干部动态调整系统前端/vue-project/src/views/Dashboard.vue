<template>
  <div class="dashboard-home">
    <a-alert
      v-if="loadError"
      type="error"
      show-icon
      message="首页数据加载失败"
      :description="loadError"
      style="margin-bottom: 16px"
    >
      <template #action>
        <a-button size="small" @click="loadDashboardData">重试</a-button>
      </template>
    </a-alert>

    <a-row :gutter="[16, 16]" class="stats-row">
      <a-col :xs="24" :sm="12" :md="6">
        <a-card :loading="statsLoading">
          <a-statistic
            title="干部总数"
            :value="stats.totalCadres ?? '—'"
            :value-style="{ color: '#1890ff' }"
          >
            <template #prefix><UserOutlined /></template>
          </a-statistic>
          <div class="stat-meta" v-if="statsMeta.totalCadres">{{ statsMeta.totalCadres }}</div>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="6">
        <a-card :loading="statsLoading">
          <a-statistic
            title="我的待填报"
            :value="stats.pendingTasks ?? '—'"
            :value-style="{ color: '#52c41a' }"
          >
            <template #prefix><FileTextOutlined /></template>
          </a-statistic>
          <div class="stat-meta" v-if="statsMeta.pendingTasks">{{ statsMeta.pendingTasks }}</div>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="6">
        <a-card :loading="statsLoading">
          <a-statistic
            title="临期/逾期任务"
            :value="stats.overdueTasks ?? '—'"
            :value-style="{ color: '#faad14' }"
          >
            <template #prefix><ClockCircleOutlined /></template>
          </a-statistic>
          <div class="stat-meta" v-if="statsMeta.overdueTasks">{{ statsMeta.overdueTasks }}</div>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="6">
        <a-card>
          <a-statistic
            title="风险预警"
            value="—"
            :value-style="{ color: '#999' }"
          >
            <template #prefix><AlertOutlined /></template>
          </a-statistic>
          <div class="stat-meta unavailable">未接入</div>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[16, 16]">
      <a-col :xs="24" :lg="14">
        <a-card title="我的待办" class="todo-card" :loading="todosLoading">
          <a-empty v-if="!todosLoading && todos.length === 0" description="暂无待填报任务" />
          <a-list v-else :data-source="todos" :split="true">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta>
                  <template #title>
                    <a @click.prevent="openTask(item)">{{ item.template_name || item.batch_name || '填报任务' }}</a>
                  </template>
                  <template #description>
                    {{ item.batch_name || '—' }} · 截止 {{ formatDeadline(item.deadline_at) }}
                    <a-tag v-if="item.is_overdue" color="error" style="margin-left: 8px">已逾期</a-tag>
                    <a-tag v-else-if="item.status === 'RETURNED'" color="warning" style="margin-left: 8px">已退回</a-tag>
                  </template>
                </a-list-item-meta>
                <template #actions>
                  <a @click.prevent="openTask(item)">去填报</a>
                </template>
              </a-list-item>
            </template>
          </a-list>
          <div v-if="todos.length > 0" class="card-footer-link">
            <a @click.prevent="router.push('/forms/tasks')">查看全部待填报</a>
          </div>
        </a-card>
      </a-col>

      <a-col :xs="24" :lg="10">
        <a-card title="常用入口" class="quick-actions-card">
          <a-row :gutter="[12, 12]">
            <a-col :span="12" v-for="action in quickActions" :key="action.key">
              <button type="button" class="action-item" @click="handleQuickAction(action.key)">
                <component :is="action.icon" style="font-size: 28px; color: #1890ff;" />
                <span>{{ action.title }}</span>
              </button>
            </a-col>
          </a-row>
        </a-card>

        <a-card title="系统说明" class="notice-card">
          <a-list size="small" :data-source="systemNotes">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-tag :color="item.color">{{ item.tag }}</a-tag>
                <span>{{ item.text }}</span>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  UserOutlined,
  FileTextOutlined,
  AlertOutlined,
  ClockCircleOutlined,
  SwapOutlined,
  ApartmentOutlined
} from '@ant-design/icons-vue'
import request from '@/utils/request'
import { formsApi } from '@/api/forms'
import { registerModelContextTools } from '@/utils/webmcp'

const router = useRouter()

const statsLoading = ref(false)
const todosLoading = ref(false)
const loadError = ref('')
const stats = ref({
  totalCadres: null,
  pendingTasks: null,
  overdueTasks: null
})
const statsMeta = ref({
  totalCadres: '',
  pendingTasks: '',
  overdueTasks: ''
})
const todos = ref([])

const quickActions = [
  { key: 'roster', title: '花名册管理', icon: UserOutlined },
  { key: 'allocation', title: '部门调配', icon: SwapOutlined },
  { key: 'organization', title: '组织架构', icon: ApartmentOutlined },
  { key: 'form-tasks', title: '我的待填报', icon: FileTextOutlined }
]

const systemNotes = [
  { tag: '调配', color: 'blue', text: '部门调配提交后立即生效，无需审批。' },
  { tag: '预警', color: 'default', text: '风险预警模块尚未接入，首页不展示虚构数字。' },
  { tag: '通知', color: 'default', text: '通知中心、个人中心与设置尚未接入。' }
]

const formatDeadline = (value) => {
  if (!value) return '未设置'
  try {
    return new Date(value).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return value
  }
}

const openTask = (item) => {
  router.push(`/forms/tasks/${item.id}/edit`)
}

const handleQuickAction = (action) => {
  const routes = {
    roster: '/cadre/roster',
    allocation: '/allocation/plan',
    organization: '/org/structure',
    'form-tasks': '/forms/tasks'
  }
  if (routes[action]) router.push(routes[action])
}

const loadDashboardData = async () => {
  statsLoading.value = true
  todosLoading.value = true
  loadError.value = ''
  statsMeta.value = { totalCadres: '', pendingTasks: '', overdueTasks: '' }

  const errors = []

  try {
    const rosterStats = await request.get('/roster/statistics/')
    stats.value.totalCadres = rosterStats.total ?? 0
    statsMeta.value.totalCadres = `覆盖 ${rosterStats.departments ?? 0} 个部门`
  } catch (error) {
    stats.value.totalCadres = null
    statsMeta.value.totalCadres = '加载失败'
    errors.push('干部总数')
  }

  try {
    const tasks = await formsApi.getMyTasks()
    const list = Array.isArray(tasks) ? tasks : (tasks?.results || [])
    const actionable = list.filter(item => ['PENDING', 'DRAFT', 'RETURNED'].includes(item.status))
    const overdue = actionable.filter(item => item.is_overdue)
    stats.value.pendingTasks = actionable.length
    stats.value.overdueTasks = overdue.length
    statsMeta.value.pendingTasks = '来自我的填报任务'
    statsMeta.value.overdueTasks = overdue.length ? '含已逾期' : '无逾期'
    todos.value = actionable
      .slice()
      .sort((a, b) => Number(b.is_overdue) - Number(a.is_overdue) || new Date(a.deadline_at) - new Date(b.deadline_at))
      .slice(0, 8)
  } catch (error) {
    stats.value.pendingTasks = null
    stats.value.overdueTasks = null
    statsMeta.value.pendingTasks = '无权限或加载失败'
    statsMeta.value.overdueTasks = '无权限或加载失败'
    todos.value = []
    // 无表单权限时不算首页致命错误
    if (error.response?.status && error.response.status !== 403) {
      errors.push('待填报任务')
    }
  } finally {
    statsLoading.value = false
    todosLoading.value = false
  }

  if (errors.length) {
    loadError.value = `以下数据未能加载：${errors.join('、')}。请确认后端服务可用后重试。`
  }
}

let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'read_openhrm_dashboard',
      title: '读取系统首页',
      description: '读取系统首页展示的统计、待办与快捷入口，不修改系统数据。',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true, untrustedContentHint: true },
      async execute() {
        return {
          statistics: stats.value,
          todos: todos.value.map(({ id, template_name, batch_name, deadline_at, status, is_overdue }) => ({
            id, template_name, batch_name, deadline_at, status, is_overdue
          })),
          quickActions: quickActions.map(({ key, title }) => ({ key, title }))
        }
      }
    },
    {
      name: 'start_openhrm_dashboard_quick_action',
      title: '打开首页快捷入口',
      description: '通过系统首页快捷入口打开对应页面，不保存或修改业务数据。',
      inputSchema: {
        type: 'object',
        properties: { key: { type: 'string', enum: ['roster', 'allocation', 'organization', 'form-tasks'] } },
        required: ['key'],
        additionalProperties: false
      },
      annotations: { readOnlyHint: true },
      async execute(input) {
        handleQuickAction(input.key)
        return { status: 'ready', key: input.key }
      }
    }
  ])
}

onMounted(() => {
  registerWebMcpTools()
  loadDashboardData()
})
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>
.dashboard-home {
  padding: 24px;
}

.stats-row {
  margin-bottom: 16px;
}

.stat-meta {
  margin-top: 8px;
  color: #8c8c8c;
  font-size: 12px;
}

.stat-meta.unavailable {
  color: #bfbfbf;
}

.todo-card,
.quick-actions-card {
  margin-bottom: 16px;
}

.notice-card {
  margin-bottom: 0;
}

.action-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 8px;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.action-item:hover {
  background: #f5f5f5;
  border-color: #d9d9d9;
}

.action-item span {
  color: #333;
  font-size: 14px;
}

.card-footer-link {
  margin-top: 12px;
  text-align: right;
}

@media (max-width: 768px) {
  .dashboard-home {
    padding: 16px;
  }
}
</style>
