<template>
  <div class="page-shell">
    <a-page-header title="优秀干部推荐下发" sub-title="按《党支部优秀干部推荐表》网页下发；填报人从花名册下拉选择，不能手填姓名。">
      <template #extra><a-button type="primary" @click="openCreator">新建并下发</a-button></template>
    </a-page-header>
    <a-table :data-source="campaigns" :columns="columns" row-key="id" :loading="loading" :pagination="{ pageSize: 10 }">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status_display }}</a-tag></template>
        <template v-else-if="column.key === 'deadline'">{{ formatDate(record.deadline_at) }}</template>
        <template v-else-if="column.key === 'progress'">{{ record.progress ? `${record.progress.submitted} / ${record.progress.total}（${record.progress.completion_rate}%）` : '—' }}</template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a-button type="link" @click="showStats(record)">查看统计</a-button>
            <a-popconfirm v-if="record.status === 'PUBLISHED'" title="关闭后将停止提交，确认关闭吗？" @confirm="close(record)">
              <a-button type="link" danger>关闭</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="creatorOpen" title="下发优秀干部推荐表" width="820px" :confirm-loading="saving" ok-text="确认下发" @ok="create">
      <a-alert type="info" show-icon :message="rulesTitle" :description="options.rules_text || defaultRules" class="form-alert" />
      <a-form layout="vertical">
        <a-form-item label="活动名称" required><a-input v-model:value="form.name" placeholder="例如：2026 年党支部优秀干部推荐" /></a-form-item>
        <a-form-item label="活动说明"><a-textarea v-model:value="form.description" :rows="2" :maxlength="2000" show-count /></a-form-item>
        <a-form-item label="截止时间" required><a-date-picker v-model:value="form.deadlineAt" show-time style="width:100%" /></a-form-item>
        <a-form-item label="每个岗位类别的推荐人数">
          <a-row :gutter="12">
            <a-col v-for="item in postCategories" :key="item.key" :span="12">
              <div class="slot-label">{{ item.label }}</div>
              <a-input-number v-model:value="form.slotConfig[item.key]" :min="0" :max="20" style="width:100%" />
            </a-col>
          </a-row>
          <div class="hint">模板默认每类 1 人（对应推荐表每空 1 人）。设为 0 表示本轮不推荐该岗位。</div>
        </a-form-item>
        <a-form-item label="本人可否推荐本人">
          <a-switch v-model:checked="form.allowSelfRecommend" checked-children="允许" un-checked-children="不允许" />
          <span class="hint inline">默认不允许推荐本人；同一人不能在同一张表的多个岗位重复推荐。</span>
        </a-form-item>
        <a-form-item label="下发范围" required>
          <a-radio-group v-model:value="form.recipientMode">
            <a-radio value="all">全部启用用户</a-radio>
            <a-radio value="users">指定人员</a-radio>
            <a-radio value="org">按支部 / 部门 / 监区</a-radio>
            <a-radio value="roles">按角色</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item v-if="form.recipientMode === 'users'" label="填报人员" required>
          <a-select v-model:value="form.userIds" mode="multiple" show-search option-filter-prop="label" :options="userOptions" placeholder="选择需要填写推荐表的人员" />
        </a-form-item>
        <a-form-item v-if="form.recipientMode === 'org'" label="接收单位" required>
          <a-select v-model:value="form.orgUnitIds" mode="multiple" show-search option-filter-prop="label" :options="orgOptions" placeholder="选择支部、部门或监区，系统自动包含下级单位成员" />
        </a-form-item>
        <a-form-item v-if="form.recipientMode === 'roles'" label="接收角色" required>
          <a-select v-model:value="form.roleCodes" mode="multiple" show-search option-filter-prop="label" :options="roleOptions" placeholder="选择角色" />
        </a-form-item>
      </a-form>
      <a-space>
        <a-button @click="preview">预览下发名单</a-button>
        <span v-if="previewCount !== null" class="hint">将创建 {{ previewCount }} 份推荐表</span>
      </a-space>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { useRouter } from 'vue-router'
import { recommendationsApi } from '@/api/recommendations'
import { registerModelContextTools } from '@/utils/webmcp'

const router = useRouter()
const campaigns = ref([])
const options = ref({ post_categories: [], users: [], roles: [], org_units: [], rules_text: '' })
const loading = ref(false)
const creatorOpen = ref(false)
const saving = ref(false)
const previewCount = ref(null)
const defaultRules = '候选人从花名册按支部/部门/监区弹出；同一人不能跨岗位重复推荐；默认不允许推荐本人。'
const rulesTitle = '填报与名额规则'
const defaultSlots = () => ({
  section_chief: 1,
  deputy_section_chief: 1,
  team_lead: 1,
  deputy_team_lead: 1,
  police_officer: 1
})
const newForm = () => ({
  name: '',
  description: '',
  deadlineAt: null,
  allowSelfRecommend: false,
  slotConfig: defaultSlots(),
  recipientMode: 'org',
  userIds: [],
  orgUnitIds: [],
  roleCodes: []
})
const form = reactive(newForm())
const columns = [
  { title: '活动名称', dataIndex: 'name' },
  { title: '状态', key: 'status', width: 100 },
  { title: '截止时间', key: 'deadline', width: 180 },
  { title: '整体进度', key: 'progress', width: 180 },
  { title: '操作', key: 'action', width: 160 }
]
const postCategories = computed(() => options.value.post_categories?.length ? options.value.post_categories : [
  { key: 'section_chief', label: '正科级领导干部' },
  { key: 'deputy_section_chief', label: '副科级领导干部' },
  { key: 'team_lead', label: '工作团队负责人（正职）' },
  { key: 'deputy_team_lead', label: '工作团队负责人（副职）' },
  { key: 'police_officer', label: '警员职级警察' }
])
const userOptions = computed(() => (options.value.users || []).map(user => ({ value: user.id, label: `${user.real_name || user.username}（${user.username}）` })))
const roleOptions = computed(() => (options.value.roles || []).map(role => ({ value: role.code, label: role.name })))
const orgOptions = computed(() => (options.value.org_units || []).map(unit => ({ value: unit.id, label: unit.label || unit.name })))
const formatDate = value => value ? new Date(value).toLocaleString() : '—'
const statusColor = value => ({ DRAFT: 'default', PUBLISHED: 'blue', CLOSED: 'green' }[value] || 'default')

const load = async () => {
  loading.value = true
  try {
    const data = await recommendationsApi.getCampaigns()
    campaigns.value = Array.isArray(data) ? data : data?.results || []
  } catch (error) {
    message.error(error.response?.data?.detail || '推荐活动加载失败')
  } finally { loading.value = false }
}
const loadOptions = async () => {
  try {
    options.value = await recommendationsApi.getOptions()
    if (options.value.defaults?.slot_config) Object.assign(form.slotConfig, options.value.defaults.slot_config)
  } catch (error) {
    message.error(error.response?.data?.detail || '下发选项加载失败')
  }
}
const openCreator = async () => {
  Object.assign(form, newForm())
  previewCount.value = null
  creatorOpen.value = true
  if (!options.value.users?.length) await loadOptions()
}
const buildPayload = () => {
  if (!form.name.trim() || !form.deadlineAt) throw new Error('请填写活动名称和截止时间')
  const payload = {
    name: form.name.trim(),
    description: form.description.trim(),
    deadline_at: new Date(form.deadlineAt).toISOString(),
    allow_self_recommend: form.allowSelfRecommend,
    slot_config: { ...form.slotConfig },
    receiver_type: 'USER',
    receiver_expr_json: {}
  }
  if (form.recipientMode === 'all') {
    payload.receiver_expr_json = { all_users: true }
  } else if (form.recipientMode === 'users') {
    if (!form.userIds.length) throw new Error('请选择填报人员')
    payload.receiver_expr_json = { user_ids: form.userIds }
  } else if (form.recipientMode === 'org') {
    if (!form.orgUnitIds.length) throw new Error('请选择支部、部门或监区')
    payload.receiver_type = 'ORG_UNIT'
    payload.receiver_expr_json = { org_unit_ids: form.orgUnitIds }
  } else {
    if (!form.roleCodes.length) throw new Error('请选择接收角色')
    payload.receiver_type = 'ORG_ROLE'
    payload.receiver_expr_json = { role_codes: form.roleCodes }
  }
  return payload
}
const preview = async () => {
  try {
    const result = await recommendationsApi.previewCampaign(buildPayload())
    previewCount.value = result.summary?.total ?? result.tasks?.length ?? 0
    message.success(`将创建 ${previewCount.value} 份推荐表`)
  } catch (error) {
    message.error(error.response?.data?.detail || error.message || '无法预览下发名单')
  }
}
const create = async () => {
  saving.value = true
  try {
    const created = await recommendationsApi.createCampaign(buildPayload())
    message.success(`已下发，共创建 ${created.progress?.total || 0} 份推荐表`)
    creatorOpen.value = false
    await load()
  } catch (error) {
    message.error(error.response?.data?.detail || error.message || '下发失败')
  } finally { saving.value = false }
}
const close = async record => {
  try {
    await recommendationsApi.closeCampaign(record.id)
    message.success('活动已关闭')
    await load()
  } catch (error) {
    message.error(error.response?.data?.detail || '关闭失败')
  }
}
const showStats = record => router.push({ name: 'RecommendStats', query: { campaign: record.id } })

const campaignSchema = {
  type: 'object',
  properties: {
    name: { type: 'string', minLength: 1, maxLength: 200 },
    description: { type: 'string', maxLength: 2000 },
    deadlineAt: { type: 'string', minLength: 1 },
    allowSelfRecommend: { type: 'boolean' },
    recipientMode: { type: 'string', enum: ['all', 'users', 'org', 'roles'] },
    userIds: { type: 'array', items: { type: 'string' } },
    orgUnitIds: { type: 'array', items: { type: 'string' } },
    roleCodes: { type: 'array', items: { type: 'string' } },
    slotConfig: { type: 'object', additionalProperties: { type: 'integer', minimum: 0, maximum: 20 } }
  },
  required: ['name', 'deadlineAt', 'recipientMode'],
  additionalProperties: false
}
const prepareCampaign = async input => {
  await loadOptions()
  const deadlineAt = dayjs(input.deadlineAt)
  if (!deadlineAt.isValid() || !deadlineAt.isAfter(dayjs())) throw new Error('截止时间必须晚于当前时间')
  Object.assign(form, newForm(), {
    name: input.name.trim(),
    description: input.description?.trim() || '',
    deadlineAt,
    allowSelfRecommend: Boolean(input.allowSelfRecommend),
    recipientMode: input.recipientMode,
    userIds: input.userIds ? [...input.userIds] : [],
    orgUnitIds: input.orgUnitIds ? [...input.orgUnitIds] : [],
    roleCodes: input.roleCodes ? [...input.roleCodes] : [],
    slotConfig: { ...defaultSlots(), ...(input.slotConfig || {}) }
  })
  creatorOpen.value = true
  await nextTick()
}
let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'list_openhrm_recommendation_campaigns', title: '读取优秀干部推荐活动',
      description: '读取优秀干部推荐活动及填报进度。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute() { await load(); return { campaigns: campaigns.value.map(({ id, name, status, deadline_at, progress }) => ({ id, name, status, deadlineAt: deadline_at, progress })) } }
    },
    {
      name: 'complete_openhrm_recommendation_dispatch', title: '下发优秀干部推荐表',
      description: '按当前或给定配置立即下发优秀干部推荐网页表单。', inputSchema: campaignSchema, annotations: { readOnlyHint: false },
      async execute(input) { await prepareCampaign(input); const created = await recommendationsApi.createCampaign(buildPayload()); creatorOpen.value = false; await load(); return { status: 'dispatched', campaign: { id: created.id, name: created.name, total: created.progress?.total } } }
    }
  ])
}
onMounted(() => { registerWebMcpTools(); load(); loadOptions() })
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>
.page-shell { padding: 8px 0; }
.form-alert { margin-bottom: 16px; }
.hint { margin-top: 8px; color: #8c8c8c; font-size: 12px; }
.hint.inline { margin-left: 8px; }
.slot-label { margin-bottom: 4px; color: #595959; }
</style>
