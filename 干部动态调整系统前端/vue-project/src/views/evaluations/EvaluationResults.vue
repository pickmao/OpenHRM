<template>
  <div class="page-shell">
    <a-page-header title="匿名评价结果分析" sub-title="仅展示满足最小样本要求的汇总结果；不提供单份答卷、原始评语或填报人信息。" />
    <a-card>
      <a-space wrap class="toolbar">
        <span>已关闭活动：</span>
        <a-select v-model:value="campaignId" :options="campaignOptions" placeholder="选择活动" style="min-width: 340px" @change="loadResults" />
      </a-space>
      <a-empty v-if="!campaignId" description="请选择一项已关闭的评价活动" />
      <template v-else>
        <a-table :data-source="results" :columns="columns" row-key="target_id" :loading="loading">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'overall'">{{ record.available ? record.overall_score : '样本不足' }}</template>
            <template v-else-if="column.key === 'samples'">{{ record.available ? `${record.valid_response_count} 份有效答卷` : '—' }}</template>
            <template v-else-if="column.key === 'action'"><a-button v-if="record.available" type="link" @click="selected = record">查看维度</a-button><span v-else class="muted">暂不生成结果</span></template>
          </template>
        </a-table>
        <a-card v-if="selected" :title="`${selected.target_name} · 维度汇总`" size="small" class="detail-card">
          <a-descriptions bordered size="small" :column="3"><a-descriptions-item label="综合得分">{{ selected.overall_score }}</a-descriptions-item><a-descriptions-item label="有效答卷">{{ selected.valid_response_count }}</a-descriptions-item><a-descriptions-item label="建议数量">{{ selected.comment_count }}（不展示原文）</a-descriptions-item></a-descriptions>
          <a-table :data-source="selected.dimensions" :columns="dimensionColumns" row-key="key" size="small" :pagination="false" class="dimension-table">
            <template #bodyCell="{ column, record }"><template v-if="column.key === 'distribution'">1分 {{ record.distribution['1'] }} · 2分 {{ record.distribution['2'] }} · 3分 {{ record.distribution['3'] }} · 4分 {{ record.distribution['4'] }} · 5分 {{ record.distribution['5'] }}</template></template>
          </a-table>
        </a-card>
      </template>
    </a-card>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { evaluationsApi } from '@/api/evaluations'
import { registerModelContextTools } from '@/utils/webmcp'

const route = useRoute()
const campaigns = ref([])
const campaignId = ref(route.query.campaign || undefined)
const results = ref([])
const selected = ref(null)
const loading = ref(false)
const columns = [
  { title: '评价对象', dataIndex: 'target_name' }, { title: '所属单位', dataIndex: 'org_name' },
  { title: '综合得分', key: 'overall', width: 120 }, { title: '有效样本', key: 'samples', width: 150 }, { title: '操作', key: 'action', width: 130 }
]
const dimensionColumns = [{ title: '维度', dataIndex: 'label' }, { title: '平均分', dataIndex: 'average_score', width: 120 }, { title: '评分分布', key: 'distribution' }]
const campaignOptions = computed(() => campaigns.value.filter(item => item.status === 'CLOSED').map(item => ({ value: item.id, label: item.name })))
const loadCampaigns = async () => {
  try {
    const data = await evaluationsApi.getCampaigns()
    campaigns.value = Array.isArray(data) ? data : data?.results || []
    if (campaignId.value && !campaignOptions.value.some(item => item.value === campaignId.value)) campaignId.value = undefined
  } catch (error) { message.error(error.response?.data?.detail || '评价活动加载失败') }
}
const loadResults = async () => {
  if (!campaignId.value) return
  selected.value = null
  loading.value = true
  try {
    const data = await evaluationsApi.getResults(campaignId.value)
    results.value = data.results || []
  } catch (error) {
    results.value = []
    message.error(error.response?.data?.detail || '结果加载失败')
  } finally { loading.value = false }
}
const resultSchema = { type: 'object', properties: { campaignId: { type: 'string', minLength: 1, description: '已关闭评价活动 UUID。' } }, required: ['campaignId'], additionalProperties: false }
const selectCampaignResults = async selectedCampaignId => {
  await loadCampaigns()
  if (!campaignOptions.value.some(item => item.value === selectedCampaignId)) throw new Error('未找到已关闭的评价活动')
  campaignId.value = selectedCampaignId
  await loadResults()
}
let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'list_openhrm_closed_evaluation_campaigns', title: '读取已关闭匿名评价活动',
      description: '读取可查看匿名汇总结果的已关闭活动。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute() { await loadCampaigns(); return { campaigns: campaignOptions.value.map(item => ({ id: item.value, name: item.label })) } }
    },
    {
      name: 'read_openhrm_evaluation_results', title: '读取匿名评价汇总结果',
      description: '读取指定已关闭活动的匿名汇总结果，不返回单份答卷、评语原文或填报人信息。', inputSchema: resultSchema, annotations: { readOnlyHint: true, untrustedContentHint: true },
      async execute(input) { await selectCampaignResults(input.campaignId); return { campaignId: campaignId.value, results: results.value.map(({ target_id, target_name, org_name, available, overall_score, valid_response_count, comment_count, dimensions }) => ({ targetId: target_id, targetName: target_name, orgName: org_name, available, overallScore: overall_score, validResponseCount: valid_response_count, commentCount: comment_count, dimensions })) } }
    },
    {
      name: 'stage_openhrm_evaluation_result_detail', title: '查看匿名评价维度汇总',
      description: '在当前页面暂存一个已生成结果的维度汇总查看，不修改任何数据。', inputSchema: { ...resultSchema, properties: { ...resultSchema.properties, targetId: { type: 'string', minLength: 1, description: '评价目标 UUID。' } }, required: ['campaignId', 'targetId'] }, annotations: { readOnlyHint: true, untrustedContentHint: true },
      async execute(input) { await selectCampaignResults(input.campaignId); const item = results.value.find(result => result.target_id === input.targetId); if (!item) throw new Error('未找到指定评价目标的汇总结果'); if (!item.available) throw new Error('该目标有效样本不足，尚未生成汇总结果'); selected.value = item; await nextTick(); return { status: 'ready', targetId: item.target_id, targetName: item.target_name, overallScore: item.overall_score, validResponseCount: item.valid_response_count, dimensions: item.dimensions } }
    },
  ])
}
onMounted(async () => { registerWebMcpTools(); await loadCampaigns(); if (campaignId.value) await loadResults() })
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>
.page-shell { padding: 8px 0; }
.toolbar { margin-bottom: 16px; }
.detail-card { margin-top: 16px; }
.dimension-table { margin-top: 16px; }
.muted { color: #8c8c8c; }
</style>
