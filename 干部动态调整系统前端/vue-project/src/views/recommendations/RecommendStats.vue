<template>
  <div class="page-shell">
    <a-page-header title="优秀干部推荐统计" sub-title="对照《党支部优秀干部统计表》：人员类别、姓名、职务职级、统计人次、推荐票数。" />
    <a-card>
      <a-space wrap class="toolbar">
        <span>推荐活动：</span>
        <a-select v-model:value="campaignId" :options="campaignOptions" placeholder="选择活动" style="min-width: 320px" @change="loadStats" />
        <span v-if="branches.length">支部 / 监区：</span>
        <a-select v-if="branches.length" v-model:value="branchName" :options="branchOptions" style="min-width: 240px" />
        <a-button :disabled="!campaignId" :loading="exporting" @click="exportExcel">导出 Excel</a-button>
      </a-space>
      <a-alert v-if="stats" type="info" show-icon class="summary" :message="`已填报 ${stats.submitted_count} / ${stats.total_count} 人次。统计人次与推荐票数按已提交推荐表汇总；同一人在同一岗位每张表计 1 票。`" />
      <a-empty v-if="!campaignId" description="请选择一项推荐活动" />
      <template v-else-if="currentBranch">
        <h3 class="sheet-title">{{ currentBranch.title }}</h3>
        <a-table
          :data-source="tableRows"
          :columns="columns"
          :pagination="false"
          :loading="loading"
          bordered
          size="middle"
          row-key="rowKey"
        />
        <div class="footer-line">监票人：　　　　　　　　监票人：</div>
      </template>
    </a-card>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { recommendationsApi } from '@/api/recommendations'
import { registerModelContextTools } from '@/utils/webmcp'

const route = useRoute()
const campaigns = ref([])
const campaignId = ref(route.query.campaign || undefined)
const stats = ref(null)
const branchName = ref(undefined)
const loading = ref(false)
const exporting = ref(false)
const columns = [
  { title: '人员类别', dataIndex: 'post_category_label', customCell: record => ({ rowSpan: record.rowSpan, style: { verticalAlign: 'middle' } }) },
  { title: '姓名', dataIndex: 'name' },
  { title: '职务职级', dataIndex: 'position_label' },
  { title: '统计人次', dataIndex: 'person_count', width: 110 },
  { title: '推荐票数', dataIndex: 'vote_count', width: 110 }
]
const campaignOptions = computed(() => campaigns.value.map(item => ({ value: item.id, label: item.name })))
const branches = computed(() => stats.value?.branches || [])
const branchOptions = computed(() => branches.value.map(item => ({ value: item.branch_name, label: item.branch_name })))
const currentBranch = computed(() => branches.value.find(item => item.branch_name === branchName.value) || branches.value[0])
const tableRows = computed(() => {
  const rows = currentBranch.value?.rows || []
  return rows.map((row, index) => {
    const prev = rows[index - 1]
    const rowSpan = prev && prev.post_category_label === row.post_category_label
      ? 0
      : rows.slice(index).filter(item => item.post_category_label === row.post_category_label).length
    return { ...row, rowKey: `${row.post_category}-${index}`, rowSpan }
  })
})

const loadCampaigns = async () => {
  try {
    const data = await recommendationsApi.getCampaigns()
    campaigns.value = Array.isArray(data) ? data : data?.results || []
  } catch (error) {
    message.error(error.response?.data?.detail || '推荐活动加载失败')
  }
}
const loadStats = async () => {
  if (!campaignId.value) return
  loading.value = true
  try {
    stats.value = await recommendationsApi.getStats(campaignId.value)
    branchName.value = stats.value.branches?.[0]?.branch_name
  } catch (error) {
    stats.value = null
    message.error(error.response?.data?.detail || '统计加载失败')
  } finally { loading.value = false }
}
const exportExcel = async () => {
  if (!campaignId.value) return
  exporting.value = true
  try {
    const blob = await recommendationsApi.exportStats(campaignId.value)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${currentBranch.value?.title || '党支部优秀干部统计表'}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    message.error(error.response?.data?.detail || '导出失败')
  } finally { exporting.value = false }
}

let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'read_openhrm_recommendation_stats', title: '读取优秀干部推荐统计',
      description: '读取当前活动按支部汇总的推荐票数和人次。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute() {
        await loadCampaigns()
        if (campaignId.value) await loadStats()
        return { campaignId: campaignId.value, submittedCount: stats.value?.submitted_count, branches: branches.value.map(item => ({ branchName: item.branch_name, submittedCount: item.submitted_count, rowCount: item.rows?.length })) }
      }
    }
  ])
}
onMounted(async () => {
  registerWebMcpTools()
  await loadCampaigns()
  if (campaignId.value) await loadStats()
})
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>
.page-shell { padding: 8px 0; }
.toolbar { margin-bottom: 16px; }
.summary { margin-bottom: 16px; }
.sheet-title { text-align: center; margin: 8px 0 16px; }
.footer-line { margin-top: 16px; color: #595959; }
</style>
