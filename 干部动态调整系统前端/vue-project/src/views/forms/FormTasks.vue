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
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { formsApi } from '@/api/forms'

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
  try { tasks.value = await formsApi.getMyTasks(status.value ? { status: status.value } : {}) } finally { loading.value = false }
}
const editTask = task => router.push({ name: 'FormOnlyOfficeTask', params: { id: task.id } })
const viewTask = task => router.push({ name: 'FormOnlyOfficeTaskView', params: { id: task.id } })
const submitTask = async task => {
  if (!task.template_has_source_file) return message.error('该任务的原始 Excel 模板文件缺失，暂时无法提交')
  try { await formsApi.submitTask(task.id); message.success('已提交填报'); loadTasks() } catch (_) { message.error('提交失败，请确认表格已经保存') }
}
onMounted(loadTasks)
</script>

<style scoped>.page-shell { padding: 8px 0; }</style>
