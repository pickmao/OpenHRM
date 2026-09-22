<template>
  <div class="page-shell">
    <a-page-header title="我的填报" sub-title="查看管理员下发的知事识人网页表单，保存草稿后提交。" />
    <a-table :data-source="tasks" :columns="columns" row-key="id" :loading="loading" :pagination="{ pageSize: 10 }">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'deadline'">{{ formatDate(record.deadline_at) }}</template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ record.status_display }}</a-tag>
          <a-tag v-if="record.remind_count" color="orange">已催办 {{ record.remind_count }} 次</a-tag>
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
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { knowingPeopleApi } from '@/api/knowingPeople'

const router = useRouter()
const tasks = ref([])
const loading = ref(false)
const columns = [
  { title: '考察批次', dataIndex: 'campaign_name' },
  { title: '表单', dataIndex: 'form_label' },
  { title: '填报身份', dataIndex: 'filler_role_label', width: 180 },
  { title: '所属支部', dataIndex: 'branch_name', width: 160 },
  { title: '截止时间', key: 'deadline', width: 180 },
  { title: '状态', key: 'status', width: 180 },
  { title: '操作', key: 'action', width: 110 }
]
const formatDate = value => value ? new Date(value).toLocaleString() : '—'
const statusColor = value => ({ PENDING: 'blue', DRAFT: 'orange', SUBMITTED: 'green', RETURNED: 'red' }[value] || 'default')
const load = async () => {
  loading.value = true
  try {
    const data = await knowingPeopleApi.getMyTasks()
    tasks.value = Array.isArray(data) ? data : data?.results || []
  } catch (error) {
    message.error(error.response?.data?.detail || '填报任务加载失败')
  } finally {
    loading.value = false
  }
}
const openTask = record => router.push({ name: 'KnowingPeopleFill', params: { id: record.id } })
onMounted(load)
</script>

<style scoped>
.page-shell { padding: 8px 16px 24px; }
</style>
