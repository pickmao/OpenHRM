<template>
  <div class="page-shell">
    <a-page-header title="我的待填报" sub-title="在线打开 Excel 填写，保存后提交" />
    <a-tabs v-model:activeKey="status" @change="loadTasks">
      <a-tab-pane key="" tab="全部" />
      <a-tab-pane key="PENDING" tab="待填报" />
      <a-tab-pane key="DRAFT" tab="草稿" />
      <a-tab-pane key="SUBMITTED" tab="已提交" />
      <a-tab-pane key="RETURNED" tab="退回修改" />
    </a-tabs>
    <a-table :data-source="tasks" :columns="columns" row-key="id" :loading="loading" :pagination="{ pageSize: 10 }">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ record.status_display }}</a-tag>
          <a-tag v-if="record.is_overdue" color="red">已逾期</a-tag>
        </template>
        <template v-else-if="column.key === 'deadline'">{{ record.deadline_at ? new Date(record.deadline_at).toLocaleString() : '未设置' }}</template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a-tooltip v-if="record.status !== 'SUBMITTED' && record.status !== 'CLOSED' && !record.template_has_source_file" title="该任务的原始 Excel 模板文件缺失，请联系管理员恢复模板后再填写">
              <a-button type="primary" size="small" disabled>模板文件缺失</a-button>
            </a-tooltip>
            <a-button v-else-if="record.status !== 'SUBMITTED' && record.status !== 'CLOSED'" type="primary" size="small" @click="editTask(record)">去填写</a-button>
            <a-button v-else size="small" @click="viewTask(record)">查看表格</a-button>
            <a-popconfirm v-if="record.status !== 'SUBMITTED' && record.status !== 'CLOSED'" title="确认提交当前填写结果吗？" @confirm="submitTask(record)">
              <a-button size="small">提交填报</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { formsApi } from '@/api/forms'
import { registerModelContextTools } from '@/utils/webmcp'

const router = useRouter()
const tasks = ref([])
const loading = ref(false)
const status = ref('')
const columns = [
  { title: '表格', dataIndex: 'template_name' },
  { title: '下发批次', dataIndex: 'batch_name' },
  { title: '状态', key: 'status', width: 140 },
  { title: '截止时间', key: 'deadline', width: 180 },
  { title: '操作', key: 'action', width: 210 }
]
const statusColor = value => ({ PENDING: 'blue', DRAFT: 'orange', SUBMITTED: 'green', RETURNED: 'red', CLOSED: 'default' }[value] || 'default')
const loadTasks = async () => {
  loading.value = true
  try { const result = await formsApi.getMyTasks(status.value ? { status: status.value } : {}); tasks.value = Array.isArray(result) ? result : result?.results || [] } finally { loading.value = false }
}
const editTask = task => router.push({ name: 'FormOnlyOfficeTask', params: { id: task.id } })
const viewTask = task => router.push({ name: 'FormOnlyOfficeTaskView', params: { id: task.id } })
const submitTask = async task => {
  if (!task.template_has_source_file) return message.error('该任务的原始 Excel 模板文件缺失，暂时无法提交')
  try { await formsApi.submitTask(task.id); message.success('已提交填报'); loadTasks() } catch (_) { message.error('提交失败，请确认表格已经保存') }
}
const statusSchema = { type: 'object', properties: { status: { type: 'string', enum: ['', 'PENDING', 'DRAFT', 'SUBMITTED', 'RETURNED', 'CLOSED'], description: '可选任务状态；空字符串代表全部' } }, additionalProperties: false }
const findTask = id => { const task = tasks.value.find(item => item.id === id); if (!task) throw new Error('未找到指定任务，请先读取我的填报任务'); return task }
let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'list_openhrm_form_tasks', title: '读取我的填报任务', description: '按可选状态读取当前用户的表单填报任务，不提交或修改任务。', inputSchema: statusSchema, annotations: { readOnlyHint: true },
      async execute(input) { status.value = input.status || ''; await loadTasks(); return { tasks: tasks.value.map(({ id, template_name, batch_name, status: taskStatus, deadline_at, template_has_source_file }) => ({ id, templateName: template_name, batchName: batch_name, status: taskStatus, deadlineAt: deadline_at, canEdit: template_has_source_file })) } }
    },
    {
      name: 'start_openhrm_form_task_editing', title: '开始填写表单', description: '打开指定任务的 OnlyOffice 编辑页面，不会提交表单。', inputSchema: { type: 'object', properties: { taskId: { type: 'integer', minimum: 1 } }, required: ['taskId'], additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute(input) { const task = findTask(input.taskId); if (!task.template_has_source_file) throw new Error('该任务的原始 Excel 模板文件缺失，无法编辑'); await router.push({ name: 'FormOnlyOfficeTask', params: { id: task.id } }); return { status: 'ready', taskId: task.id } }
    },
    {
      name: 'start_openhrm_form_task_result_view', title: '查看填报结果', description: '打开指定任务的只读填报结果页面，不会修改任务。', inputSchema: { type: 'object', properties: { taskId: { type: 'integer', minimum: 1 } }, required: ['taskId'], additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute(input) { const task = findTask(input.taskId); await router.push({ name: 'FormOnlyOfficeTaskView', params: { id: task.id } }); return { status: 'ready', taskId: task.id } }
    },
    {
      name: 'complete_openhrm_form_task_submission', title: '提交填报任务', description: '提交指定表单任务；OnlyOffice 中的内容应已保存，此操作会将任务状态变为已提交。', inputSchema: { type: 'object', properties: { taskId: { type: 'integer', minimum: 1 } }, required: ['taskId'], additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute(input) { const task = findTask(input.taskId); if (!task.template_has_source_file) throw new Error('该任务的原始 Excel 模板文件缺失，无法提交'); await formsApi.submitTask(task.id); await loadTasks(); message.success('已提交填报'); return { status: 'submitted', taskId: task.id } }
    }
  ])
}
onMounted(async () => { registerWebMcpTools(); await loadTasks() })
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>.page-shell { padding: 8px 0; }</style>
