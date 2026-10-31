<template>
  <div class="page-shell">
    <a-page-header title="我的匿名评价" sub-title="系统仅核验您是否完成评价，不会向业务人员展示您的答卷归属。" />
    <a-alert type="info" show-icon message="评分后不可修改" description="请依据实际了解情况评分；不了解的维度可不选。涉及违纪违法线索请通过专门渠道反映，不要写入匿名评价。" class="notice" />
    <a-table :data-source="tasks" :columns="columns" row-key="target_id" :loading="loading" :pagination="{ pageSize: 10 }">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'deadline'">{{ formatDate(record.deadline_at) }}</template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="record.submitted ? 'green' : record.is_open ? 'blue' : 'default'">{{ record.submitted ? '已完成' : record.is_open ? '待评价' : '暂未开放/已截止' }}</a-tag>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button v-if="!record.submitted && record.is_open" type="primary" size="small" @click="openTask(record)">开始评价</a-button>
          <span v-else class="muted">{{ record.submitted ? '已提交' : '不可提交' }}</span>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="modalOpen" :title="current ? `评价：${current.target_name}` : '匿名评价'" :confirm-loading="submitting" ok-text="匿名提交" cancel-text="取消" width="720px" @ok="submit">
      <p class="muted">{{ current?.campaign_name }} · 截止 {{ current ? formatDate(current.deadline_at) : '' }}</p>
      <a-form layout="vertical">
        <a-form-item v-for="dimension in current?.dimensions || []" :key="dimension.key" :label="dimension.label">
          <a-radio-group v-model:value="scores[dimension.key]">
            <a-radio v-for="score in [1, 2, 3, 4, 5]" :key="score" :value="score">{{ score }} 分</a-radio>
          </a-radio-group>
          <a-button type="link" size="small" @click="scores[dimension.key] = null">不了解</a-button>
        </a-form-item>
        <a-form-item label="具体建议（选填，最多 500 字）">
          <a-textarea v-model:value="comment" :maxlength="500" :rows="4" placeholder="请勿填写能识别您个人身份的经历、时间或岗位信息。" show-count />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { evaluationsApi } from '@/api/evaluations'
import { registerModelContextTools } from '@/utils/webmcp'

const tasks = ref([])
const loading = ref(false)
const modalOpen = ref(false)
const submitting = ref(false)
const current = ref(null)
const scores = ref({})
const comment = ref('')
const columns = [
  { title: '评价活动', dataIndex: 'campaign_name' },
  { title: '评价对象', dataIndex: 'target_name' },
  { title: '所属单位', dataIndex: 'org_name' },
  { title: '截止时间', key: 'deadline', width: 180 },
  { title: '状态', key: 'status', width: 150 },
  { title: '操作', key: 'action', width: 110 }
]

const formatDate = value => value ? new Date(value).toLocaleString() : '—'
const load = async () => {
  loading.value = true
  try {
    const data = await evaluationsApi.getMyTasks()
    tasks.value = Array.isArray(data) ? data : data?.results || []
  } catch (error) {
    message.error(error.response?.data?.detail || '匿名评价任务加载失败')
  } finally {
    loading.value = false
  }
}
const openTask = task => {
  current.value = task
  scores.value = Object.fromEntries((task.dimensions || []).map(item => [item.key, null]))
  comment.value = ''
  modalOpen.value = true
}
const submit = async () => {
  if (!current.value) return
  if (!Object.values(scores.value).some(score => Number.isInteger(score))) {
    return message.warning('请至少为一个维度评分')
  }
  submitting.value = true
  try {
    await evaluationsApi.submitTask(current.value.campaign_id, current.value.target_id, { scores: scores.value, comment: comment.value })
    message.success('匿名评价已提交')
    modalOpen.value = false
    await load()
  } catch (error) {
    message.error(error.response?.data?.detail || '提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

const taskSchema = {
  type: 'object',
  properties: {
    campaignId: { type: 'string', minLength: 1, description: '评价活动 UUID。' },
    targetId: { type: 'string', minLength: 1, description: '评价目标 UUID。' },
    scores: { type: 'object', minProperties: 1, additionalProperties: { type: ['integer', 'null'], minimum: 1, maximum: 5 }, description: '以当前任务返回的维度编码为键，分值为 1 至 5 或 null。' },
    comment: { type: 'string', maxLength: 500, description: '可选匿名建议；不得包含可识别填报人身份的信息。' },
  },
  required: ['campaignId', 'targetId', 'scores'],
  additionalProperties: false,
}
const findTask = input => {
  const task = tasks.value.find(item => item.campaign_id === input.campaignId && item.target_id === input.targetId)
  if (!task) throw new Error('未找到指定匿名评价任务，请先读取我的匿名评价任务')
  if (task.submitted) throw new Error('该匿名评价任务已经提交')
  if (!task.is_open) throw new Error('该匿名评价任务当前不可提交')
  return task
}
const stageTask = async input => {
  await load()
  const task = findTask(input)
  const allowed = new Set((task.dimensions || []).map(item => item.key))
  const unknown = Object.keys(input.scores).find(key => !allowed.has(key))
  if (unknown) throw new Error(`未知评价维度：${unknown}`)
  const valid = Object.values(input.scores).filter(score => Number.isInteger(score) && score >= 1 && score <= 5)
  if (!valid.length) throw new Error('请至少为一个维度评分')
  openTask(task)
  scores.value = { ...scores.value, ...input.scores }
  comment.value = input.comment || ''
  await nextTick()
  return task
}
let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'list_openhrm_anonymous_evaluation_tasks', title: '读取我的匿名评价任务',
      description: '读取当前用户可见的匿名评价任务及提交状态，不返回答卷归属信息。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true, untrustedContentHint: true },
      async execute() { await load(); return { tasks: tasks.value.map(({ campaign_id, campaign_name, target_id, target_name, org_name, deadline_at, is_open, submitted, dimensions }) => ({ campaignId: campaign_id, campaignName: campaign_name, targetId: target_id, targetName: target_name, orgName: org_name, deadlineAt: deadline_at, isOpen: is_open, submitted, dimensions })) } }
    },
    {
      name: 'stage_openhrm_anonymous_evaluation_submission', title: '配置匿名评价提交',
      description: '在当前页面配置一份匿名评价，不会提交或改变任务状态。', inputSchema: taskSchema, annotations: { readOnlyHint: false, untrustedContentHint: true },
      async execute(input) { const task = await stageTask(input); return { status: 'staged', campaignId: task.campaign_id, targetId: task.target_id, scoredDimensionCount: Object.values(input.scores).filter(Number.isInteger).length } }
    },
    {
      name: 'complete_openhrm_anonymous_evaluation_submission', title: '提交匿名评价',
      description: '提交指定匿名评价任务；提交后不可修改，系统只保留匿名汇总结果。', inputSchema: taskSchema, annotations: { readOnlyHint: false, untrustedContentHint: true },
      async execute(input) { const task = await stageTask(input); submitting.value = true; try { await evaluationsApi.submitTask(task.campaign_id, task.target_id, { scores: scores.value, comment: comment.value }); modalOpen.value = false; await load(); return { status: 'submitted', campaignId: task.campaign_id, targetId: task.target_id } } finally { submitting.value = false } }
    },
  ])
}

onMounted(() => { registerWebMcpTools(); load() })
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>
.page-shell { padding: 8px 0; }
.notice { margin-bottom: 16px; }
.muted { color: #8c8c8c; }
</style>
