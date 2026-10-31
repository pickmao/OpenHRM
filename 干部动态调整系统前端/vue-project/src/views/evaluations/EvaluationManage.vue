<template>
  <div class="page-shell">
    <a-page-header title="匿名评价活动管理" sub-title="仅显示活动整体完成进度；不显示任何个人是否提交，也不提供逐份答卷查看。">
      <template #extra><a-button type="primary" @click="openCreator">新建活动</a-button></template>
    </a-page-header>
    <a-table :data-source="campaigns" :columns="columns" row-key="id" :loading="loading" :pagination="{ pageSize: 10 }">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status_display }}</a-tag></template>
        <template v-else-if="column.key === 'deadline'">{{ formatDate(record.deadline_at) }}</template>
        <template v-else-if="column.key === 'progress'">{{ record.progress ? `${record.progress.submitted} / ${record.progress.total}（${record.progress.completion_rate}%）` : '—' }}</template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a-popconfirm v-if="record.status === 'DRAFT'" title="发布后无法调整参评范围、对象和题目，确认发布吗？" @confirm="publish(record)"><a-button type="link">发布</a-button></a-popconfirm>
            <a-popconfirm v-if="record.status === 'PUBLISHED'" title="关闭后将停止提交并开放汇总结果，确认关闭吗？" @confirm="close(record)"><a-button type="link" danger>关闭</a-button></a-popconfirm>
            <a-button v-if="record.status === 'CLOSED'" type="link" @click="showResults(record)">查看汇总</a-button>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="creatorOpen" title="新建匿名评价活动" width="760px" :confirm-loading="saving" ok-text="创建草稿" @ok="create">
      <a-alert type="warning" show-icon message="匿名保护规则" description="同一用户不能评价自己；活动发布后范围不可调整；单个对象有效样本不足时不会生成结果。" class="form-alert" />
      <a-form layout="vertical">
        <a-form-item label="活动名称" required><a-input v-model:value="form.name" placeholder="例如：2026 年度中层干部匿名民主测评" /></a-form-item>
        <a-form-item label="活动说明"><a-textarea v-model:value="form.description" :rows="2" :maxlength="2000" show-count /></a-form-item>
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item label="截止时间" required><a-date-picker v-model:value="form.deadlineAt" show-time style="width:100%" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="最小有效样本数" required><a-input-number v-model:value="form.minValidResponses" :min="2" :max="100" style="width:100%" /></a-form-item></a-col>
        </a-row>
        <a-form-item label="评价对象" required>
          <a-select v-model:value="form.targetUserIds" mode="multiple" show-search option-filter-prop="label" :loading="loadingUsers" placeholder="选择本轮被评价人员" :options="users" />
        </a-form-item>
        <a-form-item label="参评人员" required>
          <a-select v-model:value="form.evaluatorUserIds" mode="multiple" show-search option-filter-prop="label" :loading="loadingUsers" placeholder="选择有资格填写评价的人员" :options="users" />
        </a-form-item>
        <a-form-item label="评价维度">
          <a-space wrap><a-tag v-for="item in standardDimensions" :key="item.key" color="blue">{{ item.label }}</a-tag></a-space>
          <div class="hint">V1 使用统一五个维度；后续可扩展为可复用模板。</div>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { useRouter } from 'vue-router'
import { evaluationsApi } from '@/api/evaluations'
import { registerModelContextTools } from '@/utils/webmcp'

const router = useRouter()
const campaigns = ref([])
const users = ref([])
const loading = ref(false)
const loadingUsers = ref(false)
const creatorOpen = ref(false)
const saving = ref(false)
const standardDimensions = [
  { key: 'political_quality', label: '政治素质', weight: 1 },
  { key: 'performance', label: '履职能力', weight: 1 },
  { key: 'responsibility', label: '担当作为', weight: 1 },
  { key: 'collaboration', label: '协作作风', weight: 1 },
  { key: 'integrity', label: '廉洁自律', weight: 1 }
]
const newForm = () => ({ name: '', description: '', deadlineAt: null, minValidResponses: 8, targetUserIds: [], evaluatorUserIds: [] })
const form = reactive(newForm())
const columns = [
  { title: '活动名称', dataIndex: 'name' }, { title: '状态', key: 'status', width: 100 },
  { title: '对象数', dataIndex: 'target_count', width: 90 }, { title: '截止时间', key: 'deadline', width: 180 },
  { title: '整体进度', key: 'progress', width: 180 }, { title: '操作', key: 'action', width: 150 }
]

const formatDate = value => value ? new Date(value).toLocaleString() : '—'
const statusColor = value => ({ DRAFT: 'default', PUBLISHED: 'blue', CLOSED: 'green' }[value] || 'default')
const load = async () => {
  loading.value = true
  try {
    const data = await evaluationsApi.getCampaigns()
    campaigns.value = Array.isArray(data) ? data : data?.results || []
  } catch (error) {
    message.error(error.response?.data?.detail || '评价活动加载失败')
  } finally { loading.value = false }
}
const loadUsers = async () => {
  loadingUsers.value = true
  try {
    const data = await evaluationsApi.getParticipants()
    users.value = (Array.isArray(data) ? data : data?.results || []).map(user => ({ value: user.id, label: `${user.label}（${user.username}）` }))
  } catch (error) {
    message.error(error.response?.data?.detail || '参评人员加载失败')
  } finally { loadingUsers.value = false }
}
const openCreator = async () => {
  Object.assign(form, newForm())
  creatorOpen.value = true
  if (!users.value.length) await loadUsers()
}
const create = async () => {
  if (!form.name.trim() || !form.deadlineAt || !form.targetUserIds.length || !form.evaluatorUserIds.length) {
    return message.warning('请填写活动名称、截止时间、评价对象和参评人员')
  }
  saving.value = true
  try {
    await evaluationsApi.createCampaign({
      name: form.name.trim(), description: form.description.trim(), dimensions: standardDimensions,
      deadline_at: new Date(form.deadlineAt).toISOString(), min_valid_responses: form.minValidResponses,
      target_user_ids: form.targetUserIds, evaluator_user_ids: form.evaluatorUserIds
    })
    message.success('匿名评价活动草稿已创建')
    creatorOpen.value = false
    await load()
  } catch (error) {
    message.error(error.response?.data?.detail || '创建失败')
  } finally { saving.value = false }
}
const publish = async record => {
  try { await evaluationsApi.publishCampaign(record.id); message.success('活动已发布'); await load() } catch (error) { message.error(error.response?.data?.detail || '发布失败') }
}
const close = async record => {
  try { await evaluationsApi.closeCampaign(record.id); message.success('活动已关闭，结果已按匿名规则汇总'); await load() } catch (error) { message.error(error.response?.data?.detail || '关闭失败') }
}
const showResults = record => router.push({ name: 'EvaluationResults', query: { campaign: record.id } })

const campaignDraftSchema = {
  type: 'object',
  properties: {
    name: { type: 'string', minLength: 1, maxLength: 200 },
    description: { type: 'string', maxLength: 2000 },
    deadlineAt: { type: 'string', minLength: 1, description: '截止时间，ISO 日期时间字符串。' },
    minValidResponses: { type: 'integer', minimum: 2, maximum: 100 },
    targetUserIds: { type: 'array', items: { type: 'string', minLength: 1 }, minItems: 1, uniqueItems: true, description: '被评价用户 UUID 列表。' },
    evaluatorUserIds: { type: 'array', items: { type: 'string', minLength: 1 }, minItems: 1, uniqueItems: true, description: '参评用户 UUID 列表。' },
  },
  required: ['name', 'deadlineAt', 'targetUserIds', 'evaluatorUserIds'],
  additionalProperties: false,
}
const prepareCampaignDraft = async input => {
  await loadUsers()
  const knownIds = new Set(users.value.map(item => item.value))
  const unknown = [...input.targetUserIds, ...input.evaluatorUserIds].find(id => !knownIds.has(id))
  if (unknown) throw new Error(`未知用户 UUID：${unknown}`)
  const deadlineAt = dayjs(input.deadlineAt)
  if (!deadlineAt.isValid() || !deadlineAt.isAfter(dayjs())) throw new Error('截止时间必须晚于当前时间')
  Object.assign(form, { name: input.name.trim(), description: input.description?.trim() || '', deadlineAt, minValidResponses: input.minValidResponses ?? 8, targetUserIds: [...input.targetUserIds], evaluatorUserIds: [...input.evaluatorUserIds] })
  creatorOpen.value = true
  await nextTick()
}
const findCampaign = campaignId => {
  const campaign = campaigns.value.find(item => item.id === campaignId)
  if (!campaign) throw new Error('未找到指定评价活动，请先读取活动列表')
  return campaign
}
let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'list_openhrm_evaluation_campaigns', title: '读取匿名评价活动',
      description: '读取匿名评价活动及整体完成进度；不返回答卷或评价人身份。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute() { await load(); return { campaigns: campaigns.value.map(({ id, name, status, status_display, target_count, deadline_at, progress }) => ({ id, name, status, statusDisplay: status_display, targetCount: target_count, deadlineAt: deadline_at, progress })) } }
    },
    {
      name: 'read_openhrm_evaluation_participants', title: '读取可选参评人员',
      description: '读取可用于创建匿名评价活动的在职用户选项。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true, untrustedContentHint: true },
      async execute() { await loadUsers(); return { participants: users.value.map(({ value, label }) => ({ id: value, label })) } }
    },
    {
      name: 'stage_openhrm_evaluation_campaign_creation', title: '配置匿名评价活动',
      description: '在当前页面配置匿名评价活动草稿，不会保存、发布或通知参评人员。', inputSchema: campaignDraftSchema, annotations: { readOnlyHint: false, untrustedContentHint: true },
      async execute(input) { await prepareCampaignDraft(input); return { status: 'staged', name: form.name, targetCount: form.targetUserIds.length, evaluatorCount: form.evaluatorUserIds.length } }
    },
    {
      name: 'complete_openhrm_evaluation_campaign_creation', title: '创建匿名评价活动草稿',
      description: '创建匿名评价活动草稿；不会发布活动或发送任务。', inputSchema: campaignDraftSchema, annotations: { readOnlyHint: false, untrustedContentHint: true },
      async execute(input) { await prepareCampaignDraft(input); saving.value = true; try { const created = await evaluationsApi.createCampaign({ name: form.name, description: form.description, dimensions: standardDimensions, deadline_at: new Date(form.deadlineAt).toISOString(), min_valid_responses: form.minValidResponses, target_user_ids: form.targetUserIds, evaluator_user_ids: form.evaluatorUserIds }); creatorOpen.value = false; await load(); return { status: 'created', campaign: { id: created.id, name: created.name, status: created.status } } } finally { saving.value = false } }
    },
    {
      name: 'complete_openhrm_evaluation_campaign_publish', title: '发布匿名评价活动',
      description: '发布指定草稿活动并生成匿名评价任务；发布后评价范围、对象和题目不能调整。', inputSchema: { type: 'object', properties: { campaignId: { type: 'string', minLength: 1, description: '评价活动 UUID。' } }, required: ['campaignId'], additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute(input) { await load(); const campaign = findCampaign(input.campaignId); const published = await evaluationsApi.publishCampaign(campaign.id); await load(); return { status: 'published', campaign: { id: published.id, name: published.name, status: published.status } } }
    },
    {
      name: 'complete_openhrm_evaluation_campaign_close', title: '关闭匿名评价活动',
      description: '关闭指定已发布活动，停止提交并开放匿名汇总结果。', inputSchema: { type: 'object', properties: { campaignId: { type: 'string', minLength: 1, description: '评价活动 UUID。' } }, required: ['campaignId'], additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute(input) { await load(); const campaign = findCampaign(input.campaignId); const closed = await evaluationsApi.closeCampaign(campaign.id); await load(); return { status: 'closed', campaign: { id: closed.id, name: closed.name, status: closed.status } } }
    },
    {
      name: 'start_openhrm_evaluation_results', title: '打开匿名评价汇总',
      description: '打开指定已关闭活动的匿名汇总结果页面，不读取单份答卷。', inputSchema: { type: 'object', properties: { campaignId: { type: 'string', minLength: 1, description: '评价活动 UUID。' } }, required: ['campaignId'], additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute(input) { await load(); const campaign = findCampaign(input.campaignId); if (campaign.status !== 'CLOSED') throw new Error('仅已关闭活动可查看汇总结果'); await router.push({ name: 'EvaluationResults', query: { campaign: campaign.id } }); return { status: 'ready', campaignId: campaign.id } }
    },
  ])
}

onMounted(() => { registerWebMcpTools(); load() })
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>
.page-shell { padding: 8px 0; }
.form-alert { margin-bottom: 16px; }
.hint { margin-top: 8px; color: #8c8c8c; font-size: 12px; }
</style>
