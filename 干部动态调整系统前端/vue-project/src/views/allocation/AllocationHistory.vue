<template>
  <div class="allocation-page">
    <a-card title="调配历史" :bordered="false">
      <a-alert
        type="info"
        show-icon
        message="调配为直接生效模式"
        description="展示权限范围内已生效的部门调配记录，包含人员、部门、原因和操作人。"
        style="margin-bottom: 16px"
      />
      <a-space style="margin-bottom: 16px">
        <a-button @click="loadHistory">刷新</a-button>
        <a-button type="primary" @click="$router.push('/allocation/plan')">前往部门调配</a-button>
      </a-space>
      <a-alert v-if="errorText" type="error" :message="errorText" show-icon style="margin-bottom: 16px" />
      <a-table :columns="columns" :data-source="records" :loading="loading" row-key="id"
        :pagination="pagination" :scroll="{ x: 1000 }" @change="changePage">
        <template #bodyCell="{ column, text }">
          <template v-if="column.key === 'created_at'">{{ text ? new Date(text).toLocaleString('zh-CN') : '—' }}</template>
          <template v-else>{{ text || '—' }}</template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, reactive } from 'vue'
import { registerModelContextTools } from '@/utils/webmcp'
import { getTransferHistory } from '@/api/org'

const records = ref([])
const loading = ref(false)
const errorText = ref('')
const pagination = reactive({ current: 1, pageSize: 20, total: 0, showSizeChanger: false })
const columns = [
  { title: '人员', dataIndex: 'person_name', key: 'person_name', width: 140 },
  { title: '调出部门', dataIndex: 'from_department', key: 'from_department', width: 160 },
  { title: '调入部门', dataIndex: 'to_department', key: 'to_department', width: 160 },
  { title: '生效日期', dataIndex: 'effective_date', key: 'effective_date', width: 120 },
  { title: '调配原因', dataIndex: 'reason', key: 'reason', width: 260 },
  { title: '操作人', dataIndex: 'operator_name', key: 'operator_name', width: 120 },
  { title: '记录时间', dataIndex: 'created_at', key: 'created_at', width: 180 }
]
async function loadHistory() {
  loading.value = true
  errorText.value = ''
  try {
    const data = await getTransferHistory({ page: pagination.current })
    records.value = data.results || []
    pagination.total = data.count || 0
  } catch (error) {
    records.value = []
    pagination.total = 0
    errorText.value = error.response?.data?.detail || '调配历史加载失败，请重试。'
  } finally {
    loading.value = false
  }
}
function changePage(page) {
  pagination.current = page.current
  loadHistory()
}

let unregisterWebMcpTools = () => {}
onMounted(() => {
  loadHistory()
  unregisterWebMcpTools = registerModelContextTools([{
    name: 'read_openhrm_allocation_history_status',
    title: '读取调配历史状态',
    description: '读取已加载的调配历史和分页状态。',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true },
    async execute() {
      return { auditHistoryAvailable: !errorText.value, mode: 'direct_effect', records: records.value, total: pagination.total, page: pagination.current, error: errorText.value }
    }
  }])
})
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>
.allocation-page {
  min-height: calc(100vh - 48px);
  padding: 24px;
  background: #f5f7fa;
}
</style>
