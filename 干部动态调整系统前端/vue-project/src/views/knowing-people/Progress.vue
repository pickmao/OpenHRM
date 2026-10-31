<template>
  <div class="page-shell">
    <a-page-header title="知事识人填报进度" sub-title="查看填报进度、按原表规则统计成绩并导出；缺少评分来源时显示缺项。" />
    <a-card>
      <a-space wrap class="toolbar">
        <span>考察批次：</span>
        <a-select v-model:value="campaignId" :options="campaignOptions" placeholder="选择批次" style="min-width: 320px" @change="loadProgress" />
        <span>表单类型：</span>
        <a-select v-model:value="formType" allow-clear :options="formTypeOptions" placeholder="全部" style="min-width: 240px" @change="loadProgress" />
        <span>状态：</span>
        <a-select v-model:value="statusFilter" allow-clear :options="statusOptions" placeholder="全部" style="width: 140px" @change="loadProgress" />
      </a-space>
      <a-empty v-if="!campaignId" description="请选择一个考察批次" />
      <template v-else>
        <a-alert type="info" show-icon class="summary" :message="summaryText" />
        <a-row :gutter="16" class="stat-row">
          <a-col :span="12">
            <h4>按表单</h4>
            <a-table :data-source="progress?.by_form_type || []" :columns="typeColumns" row-key="form_type" size="small" :pagination="false" />
          </a-col>
          <a-col :span="12">
            <h4>按支部</h4>
            <a-table :data-source="progress?.by_branch || []" :columns="branchColumns" row-key="branch_name" size="small" :pagination="false" />
          </a-col>
        </a-row>
        <h4>任务列表</h4>
        <a-table :data-source="progress?.tasks || []" :columns="taskColumns" row-key="id" :loading="loading" :pagination="{ pageSize: 10 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status_display }}</a-tag></template>
            <template v-else-if="column.key === 'action'">
              <a-space v-if="record.can_manage">
                <a-button type="link" size="small" @click="openTask(record)">查看</a-button>
                <a-button v-if="record.status !== 'SUBMITTED'" type="link" size="small" @click="remind(record)">催办</a-button>
                <a-button v-if="record.status === 'SUBMITTED'" type="link" danger size="small" @click="openReturn(record)">退回</a-button>
              </a-space>
            </template>
          </template>
        </a-table>
        <a-space class="toolbar">
          <h4>整个批次统计</h4>
          <a-button :loading="exporting" @click="exportStatistics">导出统计表 Excel</a-button>
        </a-space>
        <a-alert class="summary" type="info" show-icon message="统计和导出覆盖整个批次，不随上方任务筛选变化。有效/缺失评价数仅统计已提交记录；综合行计七个维度的评价项数。待提交份数含待填、草稿、退回任务；尚有任务未提交或评分来源、维度未齐全时，最终分为空。" />
        <a-tabs>
          <a-tab-pane v-for="section in progress?.report_sections || []" :key="section.key" :tab="section.label">
            <a-table :data-source="section.rows" :columns="reportColumns" :row-key="row => `${row.target_id}-${row.dimension_key}`" size="small" :scroll="{ x: 1400 }" :pagination="{ pageSize: 10 }" />
          </a-tab-pane>
        </a-tabs>
        <h4>计票明细（按评价来源）</h4>
        <a-table :data-source="progress?.votes || []" :columns="voteColumns" row-key="rowKey" size="small" :pagination="{ pageSize: 10 }" />
      </template>
    </a-card>
    <a-modal v-model:open="returnOpen" title="退回重填" ok-text="确认退回" @ok="confirmReturn">
      <a-textarea v-model:value="returnReason" :rows="4" placeholder="请填写退回原因" />
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { knowingPeopleApi } from '@/api/knowingPeople'

const route = useRoute()
const router = useRouter()
const campaigns = ref([])
const campaignId = ref(route.query.campaign || undefined)
const progress = ref(null)
const loading = ref(false)
const exporting = ref(false)
const formType = ref(undefined)
const statusFilter = ref(undefined)
const returnOpen = ref(false)
const returnReason = ref('')
const returning = ref(null)
const statusOptions = [
  { value: 'PENDING', label: '待填报' },
  { value: 'DRAFT', label: '草稿' },
  { value: 'SUBMITTED', label: '已提交' },
  { value: 'RETURNED', label: '退回修改' }
]
const campaignOptions = computed(() => campaigns.value.map(item => ({ value: item.id, label: item.name })))
const formTypeOptions = computed(() => (progress.value?.catalog || []).map(item => ({ value: item.key, label: item.label })))
const summaryText = computed(() => {
  const item = progress.value?.progress
  if (!item) return ''
  return `已提交 ${item.submitted} / ${item.total}（${item.completion_rate}%）。${progress.value?.note || ''}`
})
const typeColumns = [
  { title: '表单', dataIndex: 'form_label' },
  { title: '完成率', dataIndex: 'completion_rate', width: 90, customRender: ({ text }) => `${text}%` },
  { title: '已交', dataIndex: 'submitted', width: 70 },
  { title: '总数', dataIndex: 'total', width: 70 }
]
const branchColumns = [
  { title: '支部', dataIndex: 'branch_name' },
  { title: '完成率', dataIndex: 'completion_rate', width: 90, customRender: ({ text }) => `${text}%` },
  { title: '已交', dataIndex: 'submitted', width: 70 },
  { title: '总数', dataIndex: 'total', width: 70 }
]
const taskColumns = [
  { title: '填报人', dataIndex: 'assignee_name', width: 120 },
  { title: '表单', dataIndex: 'form_label' },
  { title: '身份', dataIndex: 'filler_role_label', width: 160 },
  { title: '支部', dataIndex: 'branch_name', width: 140 },
  { title: '状态', key: 'status', width: 100 },
  { title: '催办', dataIndex: 'remind_count', width: 70 },
  { title: '操作', key: 'action', width: 180 }
]
const voteColumns = [
  { title: '表单', dataIndex: 'form_label' },
  { title: '对象', dataIndex: 'target_name' },
  { title: '评价来源', dataIndex: 'filler_role_label' },
  { title: '维度', dataIndex: 'dimension' },
  { title: '优/好', dataIndex: 'excellent', width: 80 },
  { title: '良/较好', dataIndex: 'good', width: 90 },
  { title: '中/一般', dataIndex: 'average', width: 90 },
  { title: '差', dataIndex: 'poor', width: 70 },
  { title: '合计', dataIndex: 'total', width: 70 }
]
const reportColumns = [
  { title: '对象', dataIndex: 'target_name', width: 120 },
  { title: '部门', dataIndex: 'department', width: 120 },
  { title: '维度', dataIndex: 'dimension', width: 170 },
  { title: '分组均分 / 认可度票数', dataIndex: 'group_scores_text', width: 340 },
  { title: '有效评价数', dataIndex: 'effective_count', width: 100 },
  { title: '缺失评价数', dataIndex: 'missing_count', width: 100 },
  { title: '待提交份数', dataIndex: 'pending_count', width: 100 },
  { title: '最终分', dataIndex: 'final_score', width: 90, customRender: ({ text }) => text == null ? '—' : text.toFixed(2) },
  { title: '说明', dataIndex: 'reason', width: 270 }
]
const exportStatistics = async () => {
  exporting.value = true
  try {
    const blob = await knowingPeopleApi.getStatisticsExport(campaignId.value)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = '知事识人统计表.xlsx'
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    message.error('统计表导出失败，请稍后重试')
  } finally { exporting.value = false }
}
const statusColor = value => ({ PENDING: 'blue', DRAFT: 'orange', SUBMITTED: 'green', RETURNED: 'red' }[value] || 'default')

const loadCampaigns = async () => {
  try {
    const data = await knowingPeopleApi.getCampaigns()
    campaigns.value = Array.isArray(data) ? data : data?.results || []
    if (!campaignId.value && campaigns.value[0]) campaignId.value = campaigns.value[0].id
    if (campaignId.value) await loadProgress()
  } catch (error) {
    message.error(error.response?.data?.detail || '批次加载失败')
  }
}
const loadProgress = async () => {
  if (!campaignId.value) return
  loading.value = true
  try {
    const data = await knowingPeopleApi.getProgress(campaignId.value, { form_type: formType.value, status: statusFilter.value })
    data.votes = (data.votes || []).map((row, index) => ({ ...row, rowKey: `${row.form_type}-${row.target_name}-${row.dimension}-${index}` }))
    progress.value = data
  } catch (error) {
    message.error(error.response?.data?.detail || '进度加载失败')
  } finally { loading.value = false }
}
const openTask = record => router.push({ name: 'KnowingPeopleFill', params: { id: record.id } })
const remind = async record => {
  try {
    await knowingPeopleApi.remindTask(record.id)
    message.success('已记录催办（系统暂无消息通道，请结合名单线下通知）')
    await loadProgress()
  } catch (error) {
    message.error(error.response?.data?.detail || '催办失败')
  }
}
const openReturn = record => { returning.value = record; returnReason.value = ''; returnOpen.value = true }
const confirmReturn = async () => {
  if (!returnReason.value.trim()) return message.warning('请填写退回原因')
  try {
    await knowingPeopleApi.returnTask(returning.value.id, returnReason.value.trim())
    message.success('已退回')
    returnOpen.value = false
    await loadProgress()
  } catch (error) {
    message.error(error.response?.data?.detail || '退回失败')
  }
}
onMounted(loadCampaigns)
</script>

<style scoped>
.page-shell { padding: 8px 16px 24px; }
.toolbar { margin-bottom: 16px; }
.summary { margin-bottom: 16px; }
.stat-row { margin-bottom: 16px; }
h4 { margin: 8px 0 12px; }
</style>
