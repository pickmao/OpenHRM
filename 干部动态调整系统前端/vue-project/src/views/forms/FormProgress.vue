<template>
  <div class="page-shell">
    <a-page-header title="填报任务管理" sub-title="查看谁已提交、谁尚未填报，并查看提交结果" />
    <a-table :data-source="batches" :columns="batchColumns" row-key="id" :loading="loading">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'progress'">{{ record.stats_submitted }} / {{ record.stats_total }}</template>
        <template v-else-if="column.key === 'action'"><a-button type="link" @click="showBatch(record)">查看填报情况</a-button></template>
      </template>
    </a-table>
    <a-drawer v-model:open="drawerOpen" :title="selectedBatch?.name" width="860">
      <a-descriptions v-if="dashboard || progress" bordered size="small" :column="3" class="progress-summary">
        <a-descriptions-item label="应填">{{ summary.total }}</a-descriptions-item>
        <a-descriptions-item label="已提交">{{ summary.submitted }}</a-descriptions-item>
        <a-descriptions-item label="待填/草稿">{{ summary.pending + summary.draft }}</a-descriptions-item>
        <a-descriptions-item label="退回修改">{{ summary.returned }}</a-descriptions-item>
        <a-descriptions-item label="已逾期">{{ summary.overdue }}</a-descriptions-item>
        <a-descriptions-item label="完成率">{{ summary.completion_rate ?? 0 }}%</a-descriptions-item>
      </a-descriptions>
      <a-table :data-source="tasks" :columns="taskColumns" row-key="id" :loading="loadingTasks" size="small">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'"><a-tag :color="record.status === 'SUBMITTED' ? 'green' : 'orange'">{{ record.status_display }}</a-tag></template>
          <template v-else-if="column.key === 'action'"><a-button size="small" @click="viewResult(record)">查看表格</a-button></template>
        </template>
      </a-table>
      <a-card title="未提交人员" size="small" class="pending-card">
        <a-table :data-source="pendingUsers" :columns="pendingColumns" row-key="task_id" :pagination="false" size="small">
          <template #bodyCell="{ column, record }"><template v-if="column.key === 'deadline'">{{ new Date(record.deadline_at).toLocaleString() }}<a-tag v-if="record.is_overdue" color="red" style="margin-left: 6px">逾期 {{ record.days_overdue }} 天</a-tag></template></template>
        </a-table>
      </a-card>
    </a-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { formsApi } from '@/api/forms'
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
const batchColumns = [
  { title: '下发批次', dataIndex: 'name' }, { title: '截止时间', dataIndex: 'deadline_at' },
  { title: '完成进度', key: 'progress' }, { title: '操作', key: 'action' }
]
const taskColumns = [
  { title: '填报人', dataIndex: 'assignee_name_snapshot' }, { title: '表格', dataIndex: 'template_name' },
  { title: '状态', key: 'status' }, { title: '操作', key: 'action' }
]
const pendingColumns = [
  { title: '填报对象', dataIndex: 'assignee_name' }, { title: '所属单位', dataIndex: 'org_unit' },
  { title: '表格', dataIndex: 'template_name' }, { title: '截止时间', key: 'deadline', width: 220 }
]
const summary = computed(() => dashboard.value?.summary || progress.value?.summary || { total: 0, submitted: 0, pending: 0, draft: 0, returned: 0, overdue: 0 })
const loadBatches = async () => { loading.value = true; try { const result = await formsApi.getDispatches(); batches.value = Array.isArray(result) ? result : result?.results || [] } finally { loading.value = false } }
const showBatch = async batch => {
  selectedBatch.value = batch; drawerOpen.value = true; loadingTasks.value = true
  try {
    const [legacyProgress, result, dashboardResult, pendingResult] = await Promise.all([
      formsApi.getProgress(batch.id), formsApi.getTaskResults(batch.id), formsApi.getDashboard(batch.id), formsApi.getPendingUsers(batch.id)
    ])
    progress.value = legacyProgress; tasks.value = result.tasks || []; dashboard.value = dashboardResult; pendingUsers.value = pendingResult.pending_users || []
  } finally { loadingTasks.value = false }
}
const viewResult = task => router.push({ name: 'FormOnlyOfficeTaskView', params: { id: task.id } })
const findBatch = batchId => { const batch = batches.value.find(item => item.id === batchId); if (!batch) throw new Error('未找到指定下发批次，请先读取下发批次'); return batch }
let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'list_openhrm_form_dispatches', title: '读取表单下发批次', description: '读取所有表单下发批次及其截止时间，不修改数据。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute() { await loadBatches(); return { batches: batches.value.map(({ id, name, deadline_at, status }) => ({ id, name, deadlineAt: deadline_at, status })) } }
    },
    {
      name: 'read_openhrm_form_dispatch_progress', title: '读取填报进度', description: '读取一个下发批次的完成汇总、任务状态和待办人员，不修改数据。', inputSchema: { type: 'object', properties: { batchId: { type: 'integer', minimum: 1 } }, required: ['batchId'], additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute(input) { const batch = findBatch(input.batchId); await showBatch(batch); return { batch: { id: batch.id, name: batch.name }, summary: summary.value, tasks: tasks.value.map(({ id, assignee_name_snapshot, template_name, status }) => ({ id, assigneeName: assignee_name_snapshot, templateName: template_name, status })), pendingUsers: pendingUsers.value.map(({ assignee_name, org_unit, template_name, deadline_at }) => ({ assigneeName: assignee_name, orgUnit: org_unit, templateName: template_name, deadlineAt: deadline_at })) } }
    },
    {
      name: 'start_openhrm_form_result_view', title: '查看填报结果', description: '打开指定任务的只读填报结果页面，不会修改表单。', inputSchema: { type: 'object', properties: { taskId: { type: 'integer', minimum: 1 } }, required: ['taskId'], additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute(input) { const task = tasks.value.find(item => item.id === input.taskId); if (!task) throw new Error('请先读取该批次的填报进度，再指定任务 ID'); viewResult(task); return { status: 'ready', taskId: task.id } }
    }
  ])
}
onMounted(async () => { registerWebMcpTools(); await loadBatches() })
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>.page-shell { padding: 8px 0; }.progress-summary, .pending-card { margin-bottom: 16px; }</style>
