<template>
  <div class="page-shell">
    <a-page-header title="我的推荐表" sub-title="从花名册下拉选择本支部 / 部门 / 监区人员，不能手填姓名。" />
    <a-table :data-source="tasks" :columns="columns" row-key="id" :loading="loading" :pagination="{ pageSize: 10 }">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'deadline'">{{ formatDate(record.deadline_at) }}</template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ record.status_display }}</a-tag>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button v-if="record.status !== 'SUBMITTED' && record.is_open" type="primary" size="small" @click="openTask(record)">去填写</a-button>
          <a-button v-else size="small" @click="openTask(record)">查看</a-button>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { recommendationsApi } from '@/api/recommendations'
import { registerModelContextTools } from '@/utils/webmcp'

const router = useRouter()
const tasks = ref([])
const loading = ref(false)
const columns = [
  { title: '活动', dataIndex: 'campaign_name' },
  { title: '所属范围', dataIndex: 'branch_name' },
  { title: '截止时间', key: 'deadline', width: 180 },
  { title: '状态', key: 'status', width: 120 },
  { title: '操作', key: 'action', width: 110 }
]
const formatDate = value => value ? new Date(value).toLocaleString() : '—'
const statusColor = value => ({ PENDING: 'blue', DRAFT: 'orange', SUBMITTED: 'green' }[value] || 'default')
const load = async () => {
  loading.value = true
  try {
    const data = await recommendationsApi.getMyTasks()
    tasks.value = Array.isArray(data) ? data : data?.results || []
  } catch (error) {
    message.error(error.response?.data?.detail || '推荐任务加载失败')
  } finally { loading.value = false }
}
const openTask = record => router.push({ name: 'RecommendFill', params: { id: record.id } })
let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'list_openhrm_recommendation_tasks', title: '读取我的优秀干部推荐表',
      description: '读取当前用户的优秀干部推荐填报任务。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute() { await load(); return { tasks: tasks.value.map(({ id, campaign_name, branch_name, status, deadline_at }) => ({ id, campaignName: campaign_name, branchName: branch_name, status, deadlineAt: deadline_at })) } }
    },
    {
      name: 'start_openhrm_recommendation_fill', title: '打开优秀干部推荐表',
      description: '打开指定推荐表填写页。', inputSchema: { type: 'object', properties: { taskId: { type: 'string', minLength: 1 } }, required: ['taskId'], additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute(input) { const task = tasks.value.find(item => item.id === input.taskId); if (!task) throw new Error('未找到指定推荐任务'); await router.push({ name: 'RecommendFill', params: { id: task.id } }); return { status: 'ready', taskId: task.id } }
    }
  ])
}
onMounted(() => { registerWebMcpTools(); load() })
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>
.page-shell { padding: 8px 0; }
</style>
