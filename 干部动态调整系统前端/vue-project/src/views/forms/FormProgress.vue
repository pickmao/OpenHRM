<template>
  <div class="page-shell">
    <a-page-header
      title="填报任务管理"
      sub-title="设置与延长截止时间，查看填报人数完成率及各支部进度"
    />

    <a-table :data-source="batches" :columns="batchColumns" row-key="id" :loading="loading">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'deadline'">
          <div>{{ formatDateTime(record.deadline_at) }}</div>
          <a-tag v-if="record.status === 'CLOSED'" color="default">已关闭</a-tag>
          <a-tag v-else-if="isPast(record.deadline_at)" color="red">已过截止</a-tag>
        </template>
        <template v-else-if="column.key === 'taskProgress'">
          <div class="rate-line">
            <span>{{ record.stats_submitted || 0 }} / {{ record.stats_total || 0 }}</span>
            <a-progress
              :percent="taskRate(record)"
              size="small"
              style="width: 120px; margin: 0"
            />
          </div>
        </template>
        <template v-else-if="column.key === 'peopleProgress'">
          <div v-if="peopleStatsMap[record.id]" class="rate-line">
            <span>
              {{ peopleStatsMap[record.id].submitted }} / {{ peopleStatsMap[record.id].total }}
            </span>
            <a-progress
              :percent="peopleStatsMap[record.id].completion_rate"
              size="small"
              status="active"
              style="width: 120px; margin: 0"
            />
          </div>
          <span v-else class="muted">打开详情查看</span>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a-button type="link" @click="showBatch(record)">查看填报情况</a-button>
            <a-button
              v-if="record.status !== 'CLOSED'"
              type="link"
              @click="openExtension(record)"
            >
              延长截止时间
            </a-button>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="extensionOpen"
      title="延长截止时间"
      :confirm-loading="extending"
      ok-text="确认延期"
      cancel-text="取消"
      @ok="extendDeadline"
    >
      <p><strong>{{ extensionBatch?.name }}</strong></p>
      <p>原截止时间：{{ extensionBatch ? formatDateTime(extensionBatch.deadline_at) : '' }}</p>
      <a-date-picker
        v-model:value="newDeadline"
        show-time
        style="width: 100%"
        placeholder="选择新的截止时间（须晚于原截止与当前时间）"
      />
    </a-modal>

    <a-drawer v-model:open="drawerOpen" :title="selectedBatch?.name" width="920">
      <a-alert
        v-if="selectedBatch"
        type="info"
        show-icon
        class="progress-summary"
        :message="`截止时间：${formatDateTime(selectedBatch.deadline_at)}`"
        :description="selectedBatch.status === 'CLOSED' ? '该批次已关闭，不能再延长截止时间。' : '可在列表中点击「延长截止时间」手动延期，未关闭任务会同步更新。'"
      />

      <a-row :gutter="16" class="progress-summary">
        <a-col :span="8">
          <a-card size="small">
            <a-statistic title="表格完成率" :value="summary.completion_rate ?? 0" suffix="%" />
            <div class="stat-sub">已提交 {{ summary.submitted }} / 应填 {{ summary.total }}</div>
          </a-card>
        </a-col>
        <a-col :span="8">
          <a-card size="small">
            <a-statistic
              title="填报人数完成率"
              :value="dashboard?.people_summary?.completion_rate ?? 0"
              suffix="%"
              :value-style="{ color: '#1890ff' }"
            />
            <div class="stat-sub">
              已完成 {{ dashboard?.people_summary?.submitted ?? 0 }} /
              应填人数 {{ dashboard?.people_summary?.total ?? 0 }}
            </div>
          </a-card>
        </a-col>
        <a-col :span="8">
          <a-card size="small">
            <a-statistic title="已逾期任务" :value="summary.overdue ?? 0" :value-style="{ color: '#cf1322' }" />
            <div class="stat-sub">待填/草稿 {{ (summary.pending || 0) + (summary.draft || 0) }} · 退回 {{ summary.returned || 0 }}</div>
          </a-card>
        </a-col>
      </a-row>

      <a-card title="各支部完成百分比" size="small" class="progress-summary">
        <p class="hint">
          按接收人去重统计：该人在本批次全部表格都提交后才计为完成。单位任务、已关闭任务不计入人数。
        </p>
        <a-empty
          v-if="!(dashboard?.branch_stats || []).length"
          description="暂无支部进度数据"
          :image-style="{ height: '48px' }"
        />
        <a-table
          v-else
          :data-source="dashboard.branch_stats"
          :columns="branchColumns"
          :row-key="record => record.branch_id || 'unassigned'"
          :pagination="false"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'rate'">
              <a-progress :percent="record.completion_rate" />
            </template>
          </template>
        </a-table>
      </a-card>

      <a-table
        :data-source="tasks"
        :columns="taskColumns"
        row-key="id"
        :loading="loadingTasks"
        size="small"
        class="progress-summary"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'SUBMITTED' ? 'green' : 'orange'">
              {{ record.status_display }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-button size="small" @click="viewResult(record)">查看表格</a-button>
          </template>
        </template>
      </a-table>

      <a-card title="未提交人员" size="small" class="pending-card">
        <a-table
          :data-source="pendingUsers"
          :columns="pendingColumns"
          row-key="task_id"
          :pagination="false"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'deadline'">
              {{ formatDateTime(record.deadline_at) }}
              <a-tag v-if="record.is_overdue" color="red" style="margin-left: 6px">
                逾期 {{ record.days_overdue }} 天
              </a-tag>
            </template>
          </template>
        </a-table>
      </a-card>
    </a-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { formsApi } from '@/api/forms'
import { message } from 'ant-design-vue'
import { registerModelContextTools } from '@/utils/webmcp'

const router = useRouter()
const batches = ref([])
const loading = ref(false)
const loadingTasks = ref(false)
const drawerOpen = ref(false)
const selectedBatch = ref(null)
const progress = ref(null)
const dashboard = ref(null)
const tasks = ref([])
const pendingUsers = ref([])
const extensionOpen = ref(false)
const extensionBatch = ref(null)
const newDeadline = ref(null)
const extending = ref(false)
const peopleStatsMap = reactive({})

const branchColumns = [
  { title: '支部', dataIndex: 'branch_name' },
  { title: '应填人数', dataIndex: 'total', width: 100 },
  { title: '已完成人数', dataIndex: 'submitted', width: 110 },
  { title: '完成比例', key: 'rate', width: 220 }
]

const batchColumns = [
  { title: '下发批次', dataIndex: 'name' },
  { title: '截止时间', key: 'deadline', width: 200 },
  { title: '表格完成率', key: 'taskProgress', width: 220 },
  { title: '人数完成率', key: 'peopleProgress', width: 220 },
  { title: '操作', key: 'action', width: 220 }
]

const taskColumns = [
  { title: '填报人', dataIndex: 'assignee_name_snapshot' },
  { title: '表格', dataIndex: 'template_name' },
  { title: '状态', key: 'status', width: 120 },
  { title: '操作', key: 'action', width: 100 }
]

const pendingColumns = [
  { title: '填报对象', dataIndex: 'assignee_name' },
  { title: '所属单位', dataIndex: 'org_unit' },
  { title: '表格', dataIndex: 'template_name' },
  { title: '截止时间', key: 'deadline', width: 240 }
]

const summary = computed(() => dashboard.value?.summary || progress.value?.summary || {
  total: 0, submitted: 0, pending: 0, draft: 0, returned: 0, overdue: 0, completion_rate: 0
})

const formatDateTime = (value) => {
  if (!value) return '-'
  try { return new Date(value).toLocaleString('zh-CN', { hour12: false }) } catch { return value }
}
const isPast = (value) => value && new Date(value).getTime() < Date.now()
const taskRate = (record) => {
  if (!record.stats_total) return 0
  return Math.round((record.stats_submitted * 10000) / record.stats_total) / 100
}

const openExtension = (batch) => {
  extensionBatch.value = batch
  newDeadline.value = null
  extensionOpen.value = true
}

const extendDeadline = async () => {
  if (!newDeadline.value) return message.warning('请选择新的截止时间')
  const date = new Date(newDeadline.value)
  if (date <= new Date(extensionBatch.value.deadline_at) || date <= new Date()) {
    return message.warning('新截止时间必须晚于原截止时间和当前时间')
  }
  extending.value = true
  try {
    const batch = await formsApi.extendDeadline(extensionBatch.value.id, date.toISOString())
    extensionOpen.value = false
    message.success('截止时间已延长，未关闭任务已同步更新')
    await loadBatches()
    if (drawerOpen.value && selectedBatch.value?.id === batch.id) await showBatch(batch)
  } catch (error) {
    message.error(error.response?.data?.detail || '延长截止时间失败')
  } finally {
    extending.value = false
  }
}

const loadPeopleStats = async (batchList) => {
  await Promise.all(batchList.map(async (batch) => {
    try {
      const data = await formsApi.getDashboard(batch.id)
      peopleStatsMap[batch.id] = data.people_summary || { total: 0, submitted: 0, completion_rate: 0 }
    } catch (_) {
      peopleStatsMap[batch.id] = null
    }
  }))
}

const loadBatches = async () => {
  loading.value = true
  try {
    const result = await formsApi.getDispatches()
    batches.value = Array.isArray(result) ? result : result?.results || []
    await loadPeopleStats(batches.value)
  } finally {
    loading.value = false
  }
}

const showBatch = async (batch) => {
  selectedBatch.value = batch
  drawerOpen.value = true
  loadingTasks.value = true
  progress.value = null
  dashboard.value = null
  tasks.value = []
  pendingUsers.value = []
  try {
    const [legacyProgress, result, dashboardResult, pendingResult] = await Promise.all([
      formsApi.getProgress(batch.id),
      formsApi.getTaskResults(batch.id),
      formsApi.getDashboard(batch.id),
      formsApi.getPendingUsers(batch.id)
    ])
    progress.value = legacyProgress
    tasks.value = result.tasks || []
    dashboard.value = dashboardResult
    pendingUsers.value = pendingResult.pending_users || []
    if (dashboardResult?.people_summary) {
      peopleStatsMap[batch.id] = dashboardResult.people_summary
    }
  } finally {
    loadingTasks.value = false
  }
}

const viewResult = (task) => router.push({ name: 'FormOnlyOfficeTaskView', params: { id: task.id } })
const findBatch = (batchId) => {
  const batch = batches.value.find(item => item.id === batchId)
  if (!batch) throw new Error('未找到指定下发批次，请先读取下发批次')
  return batch
}

let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'list_openhrm_form_dispatches',
      title: '读取表单下发批次',
      description: '读取所有表单下发批次及其截止时间，不修改数据。',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true },
      async execute() {
        await loadBatches()
        return {
          batches: batches.value.map(({ id, name, deadline_at, status }) => ({
            id, name, deadlineAt: deadline_at, status,
            peopleSummary: peopleStatsMap[id] || null
          }))
        }
      }
    },
    {
      name: 'read_openhrm_form_dispatch_progress',
      title: '读取填报进度',
      description: '读取一个下发批次的完成汇总、任务状态和待办人员，不修改数据。',
      inputSchema: {
        type: 'object',
        properties: { batchId: { type: 'string', minLength: 1, description: '下发批次 UUID。' } },
        required: ['batchId'],
        additionalProperties: false
      },
      annotations: { readOnlyHint: true },
      async execute(input) {
        const batch = findBatch(input.batchId)
        await showBatch(batch)
        return {
          batch: { id: batch.id, name: batch.name },
          summary: summary.value,
          peopleSummary: dashboard.value?.people_summary || null,
          branchStats: dashboard.value?.branch_stats || [],
          tasks: tasks.value.map(({ id, assignee_name_snapshot, template_name, status }) => ({
            id, assigneeName: assignee_name_snapshot, templateName: template_name, status
          })),
          pendingUsers: pendingUsers.value.map(({ assignee_name, org_unit, template_name, deadline_at }) => ({
            assigneeName: assignee_name, orgUnit: org_unit, templateName: template_name, deadlineAt: deadline_at
          }))
        }
      }
    },
    {
      name: 'start_openhrm_form_result_view',
      title: '查看填报结果',
      description: '打开指定任务的只读填报结果页面，不会修改表单。',
      inputSchema: {
        type: 'object',
        properties: { taskId: { type: 'string', minLength: 1, description: '填报任务 UUID。' } },
        required: ['taskId'],
        additionalProperties: false
      },
      annotations: { readOnlyHint: true },
      async execute(input) {
        const task = tasks.value.find(item => item.id === input.taskId)
        if (!task) throw new Error('请先读取该批次的填报进度，再指定任务 ID')
        viewResult(task)
        return { status: 'ready', taskId: task.id }
      }
    }
  ])
}

onMounted(async () => {
  registerWebMcpTools()
  await loadBatches()
})
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>
.page-shell { padding: 24px; }
.progress-summary, .pending-card { margin-bottom: 16px; }
.rate-line { display: flex; align-items: center; gap: 8px; }
.stat-sub { margin-top: 8px; color: #8c8c8c; font-size: 12px; }
.hint { color: #8c8c8c; font-size: 12px; margin-bottom: 12px; }
.muted { color: #bfbfbf; font-size: 12px; }
</style>
