<template>
  <div class="page-shell">
    <a-page-header title="知事识人任务下发" sub-title="按附件8自动匹配填报人，也可增删人员后一键下发网页表单。">
      <template #extra><a-button type="primary" @click="openCreator">新建考察批次并下发</a-button></template>
    </a-page-header>
    <a-table :data-source="campaigns" :columns="columns" row-key="id" :loading="loading" :pagination="{ pageSize: 10 }">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status_display }}</a-tag></template>
        <template v-else-if="column.key === 'forms'">{{ (record.form_type_labels || []).join('、') }}</template>
        <template v-else-if="column.key === 'deadline'">{{ formatDate(record.deadline_at) }}</template>
        <template v-else-if="column.key === 'progress'">{{ record.progress ? `${record.progress.submitted} / ${record.progress.total}（${record.progress.completion_rate}%）` : '—' }}</template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a-button type="link" @click="goProgress(record)">填报进度</a-button>
            <a-popconfirm v-if="record.status === 'PUBLISHED'" title="关闭后将停止提交，确认关闭吗？" @confirm="close(record)">
              <a-button type="link" danger>关闭</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="creatorOpen" title="下发知事识人填报表" width="980px" :confirm-loading="saving" ok-text="确认下发" @ok="create">
      <a-alert type="info" show-icon message="附件8匹配规则" :description="options.rules_text" class="form-alert" />
      <a-form layout="vertical">
        <a-row :gutter="12">
          <a-col :span="12"><a-form-item label="批次名称" required><a-input v-model:value="form.name" placeholder="例如：2026 年知事识人考察" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="年度"><a-input v-model:value="form.year" placeholder="2026" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="考察开始日期"><a-date-picker v-model:value="form.periodStart" style="width:100%" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="考察结束日期"><a-date-picker v-model:value="form.periodEnd" style="width:100%" /></a-form-item></a-col>
          <a-col :span="24"><a-form-item label="说明"><a-textarea v-model:value="form.description" :rows="2" :maxlength="2000" show-count /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="截止时间" required><a-date-picker v-model:value="form.deadlineAt" show-time style="width:100%" /></a-form-item></a-col>
          <a-col :span="12">
            <a-form-item label="按支部筛选（可选）">
              <a-select v-model:value="form.branchIds" mode="multiple" allow-clear show-search option-filter-prop="label" :options="branchOptions" placeholder="不选则匹配全部党支部/中层" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="勾选要下发的表单" required>
          <a-checkbox-group v-model:value="form.formTypes" class="type-group">
            <div v-for="item in formTypes" :key="item.key" class="type-item">
              <a-checkbox :value="item.key">
                {{ item.label }}
                <a-tag v-if="item.manual_only" color="orange">需手动选人</a-tag>
              </a-checkbox>
              <div class="hint">{{ item.rule }}</div>
            </div>
          </a-checkbox-group>
        </a-form-item>
        <a-form-item v-if="form.formTypes.includes('ATTACHMENT_7_3')" label="附件7-3 填报人（政工领导）">
          <a-select v-model:value="form.extra73" mode="multiple" show-search option-filter-prop="label" :options="userOptions" placeholder="附件8未列，需手动勾选" />
        </a-form-item>
        <a-form-item v-if="form.formTypes.includes('ATTACHMENT_1')" label="附件1 谈话测评填报人">
          <a-select v-model:value="form.extra1" mode="multiple" show-search option-filter-prop="label" :options="userOptions" placeholder="由管理员指定谈话人员" />
        </a-form-item>
      </a-form>
      <a-space class="preview-bar">
        <a-button @click="preview">按附件8预览名单</a-button>
        <span v-if="previewData" class="hint">将创建 {{ previewTotal }} 份任务</span>
      </a-space>
      <div v-if="previewData" class="preview-box">
        <div v-for="group in previewData.groups" :key="group.form_type" class="preview-group">
          <h4>{{ group.form_label }}（{{ group.recipients.length }} 人）</h4>
          <a-alert v-for="(warning, index) in group.warnings" :key="'w'+index" type="warning" show-icon :message="warning" class="mini-alert" />
          <a-alert v-for="(item, index) in group.unmatched" :key="'u'+index" type="warning" show-icon :message="`${item.name}：${item.reason}`" class="mini-alert" />
          <a-table :data-source="group.recipients" :columns="previewColumns" size="small" :row-key="item => `${item.user_id}-${item.branch_id || ''}`" :pagination="false">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'role'">
                <a-select v-model:value="record.filler_role" :options="roleOptions" style="width:180px" />
              </template>
              <template v-else-if="column.key === 'targets'">
                <a-tooltip :title="(record.target_names || []).join('、')">{{ record.target_count ?? '确认时生成' }}</a-tooltip>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-button type="link" danger size="small" @click="removeRecipient(group, record)">移除</a-button>
              </template>
            </template>
          </a-table>
        </div>
        <a-space align="start" class="add-row">
          <a-select v-model:value="addForm.formType" style="width:280px" :options="selectedTypeOptions" placeholder="表单类型" />
          <a-select v-model:value="addForm.userId" show-search option-filter-prop="label" style="width:240px" :options="userOptions" placeholder="增加填报人" />
          <a-select v-model:value="addForm.branchId" allow-clear show-search option-filter-prop="label" style="width:220px" :options="branchOptions" placeholder="所属支部（可选）" />
          <a-select v-model:value="addForm.role" style="width:180px" :options="roleOptions" placeholder="填报身份" />
          <a-button @click="addRecipient">加入名单</a-button>
        </a-space>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { useRouter } from 'vue-router'
import { knowingPeopleApi } from '@/api/knowingPeople'

const router = useRouter()
const campaigns = ref([])
const options = ref({ form_types: [], users: [], branches: [], rules_text: '' })
const loading = ref(false)
const creatorOpen = ref(false)
const saving = ref(false)
const previewData = ref(null)
const addForm = reactive({ formType: undefined, userId: undefined, branchId: undefined, role: 'MANUAL' })
const newForm = () => ({
  name: '',
  year: String(new Date().getFullYear()),
  description: '',
  periodStart: null,
  periodEnd: null,
  deadlineAt: null,
  formTypes: ['ATTACHMENT_2', 'ATTACHMENT_3'],
  branchIds: [],
  extra73: [],
  extra1: []
})
const form = reactive(newForm())
const columns = [
  { title: '批次名称', dataIndex: 'name' },
  { title: '年度', dataIndex: 'year', width: 90 },
  { title: '表单', key: 'forms' },
  { title: '状态', key: 'status', width: 90 },
  { title: '截止时间', key: 'deadline', width: 180 },
  { title: '进度', key: 'progress', width: 170 },
  { title: '操作', key: 'action', width: 160 }
]
const previewColumns = [
  { title: '填报人', dataIndex: 'user_name' },
  { title: '账号', dataIndex: 'username', width: 120 },
  { title: '填报身份（用于分组统计）', key: 'role', width: 200 },
  { title: '支部', dataIndex: 'branch_name', width: 160 },
  { title: '被评对象数', key: 'targets', width: 110 },
  { title: '操作', key: 'action', width: 80 }
]
const formTypes = computed(() => options.value.form_types || [])
const roleOptions = computed(() => (options.value.filler_roles || []).map(item => ({ value: item.key, label: item.label })))
watch(() => [form.formTypes, form.branchIds, form.extra73, form.extra1], () => { previewData.value = null }, { deep: true })
const userOptions = computed(() => (options.value.users || []).map(user => ({ value: user.id, label: `${user.real_name || user.username}（${user.username}）` })))
const branchOptions = computed(() => (options.value.branches || []).map(unit => ({ value: unit.id, label: unit.label || unit.name })))
const selectedTypeOptions = computed(() => formTypes.value.filter(item => form.formTypes.includes(item.key)).map(item => ({ value: item.key, label: item.label })))
const previewTotal = computed(() => (previewData.value?.groups || []).reduce((sum, group) => sum + group.recipients.length, 0))
const formatDate = value => value ? new Date(value).toLocaleString() : '—'
const statusColor = value => ({ DRAFT: 'default', PUBLISHED: 'blue', CLOSED: 'green' }[value] || 'default')

const load = async () => {
  loading.value = true
  try {
    const data = await knowingPeopleApi.getCampaigns()
    campaigns.value = Array.isArray(data) ? data : data?.results || []
  } catch (error) {
    message.error(error.response?.data?.detail || '批次加载失败')
  } finally { loading.value = false }
}
const loadOptions = async () => {
  try {
    options.value = await knowingPeopleApi.getOptions()
  } catch (error) {
    message.error(error.response?.data?.detail || '下发选项加载失败')
  }
}
const openCreator = async () => {
  Object.assign(form, newForm())
  previewData.value = null
  creatorOpen.value = true
  if (!options.value.users?.length) await loadOptions()
}
const extraByType = () => {
  const extra = {}
  if (form.extra73.length) extra.ATTACHMENT_7_3 = form.extra73
  if (form.extra1.length) extra.ATTACHMENT_1 = form.extra1
  return extra
}
const basePayload = () => ({
  name: form.name.trim(),
  year: form.year.trim(),
  description: form.description.trim(),
  period_start: form.periodStart ? dayjs(form.periodStart).format('YYYY-MM-DD') : null,
  period_end: form.periodEnd ? dayjs(form.periodEnd).format('YYYY-MM-DD') : null,
  deadline_at: form.deadlineAt ? new Date(form.deadlineAt).toISOString() : undefined,
  form_types: [...form.formTypes],
  branch_ids: [...form.branchIds],
  extra_user_ids_by_type: extraByType()
})
const preview = async () => {
  if (!form.formTypes.length) return message.warning('请勾选至少一种表单')
  try {
    previewData.value = await knowingPeopleApi.previewCampaign(basePayload())
    message.success(`预览完成，共 ${previewTotal.value} 人`)
  } catch (error) {
    message.error(error.response?.data?.detail || error.response?.data?.form_types?.[0] || '预览失败')
  }
}
const removeRecipient = (group, record) => {
  group.recipients = group.recipients.filter(item => item !== record)
}
const addRecipient = () => {
  if (!previewData.value) return message.warning('请先预览名单')
  if (!addForm.formType || !addForm.userId) return message.warning('请选择表单和人员')
  const group = previewData.value.groups.find(item => item.form_type === addForm.formType)
  if (!group) return
  if (group.recipients.some(item => item.user_id === addForm.userId && (item.branch_id || null) === (addForm.branchId || null))) return message.warning('该人员已在此支部名单中')
  const user = (options.value.users || []).find(item => item.id === addForm.userId)
  const branch = (options.value.branches || []).find(item => item.id === addForm.branchId)
  group.recipients.push({
    user_id: addForm.userId,
    user_name: user?.real_name || user?.username,
    username: user?.username,
    form_type: addForm.formType,
    filler_role: addForm.role || 'MANUAL',
    filler_role_label: roleOptions.value.find(item => item.value === addForm.role)?.label || '管理员指定',
    branch_id: addForm.branchId || null,
    branch_name: branch?.name || '',
    source: '管理员指定'
  })
}
const create = async () => {
  if (!form.name.trim() || !form.deadlineAt) return message.warning('请填写批次名称和截止时间')
  if (!form.formTypes.length) return message.warning('请勾选至少一种表单')
  if (!previewData.value) return message.warning('请先按附件8预览并核对名单')
  saving.value = true
  try {
    const payload = basePayload()
    if (previewData.value) {
      payload.recipients = previewData.value.groups.flatMap(group => group.recipients.map(item => ({
        form_type: item.form_type,
        user_id: item.user_id,
        branch_id: item.branch_id,
        filler_role: item.filler_role,
        source: item.source
      })))
    }
    const created = await knowingPeopleApi.createCampaign(payload)
    message.success(`已下发，共创建 ${created.progress?.total || 0} 份任务`)
    creatorOpen.value = false
    await load()
  } catch (error) {
    const data = error.response?.data
    message.error(data?.detail || data?.recipients?.[0] || data?.deadline_at?.[0] || '下发失败')
  } finally { saving.value = false }
}
const close = async record => {
  try {
    await knowingPeopleApi.closeCampaign(record.id)
    message.success('批次已关闭')
    await load()
  } catch (error) {
    message.error(error.response?.data?.detail || '关闭失败')
  }
}
const goProgress = record => router.push({ name: 'KnowingPeopleProgress', query: { campaign: record.id } })
onMounted(() => { load(); loadOptions() })
</script>

<style scoped>
.page-shell { padding: 8px 16px 24px; }
.form-alert { margin-bottom: 16px; }
.hint { color: #8c8c8c; font-size: 12px; }
.type-group { display: block; width: 100%; }
.type-item { margin-bottom: 8px; }
.preview-bar { margin: 8px 0 12px; }
.preview-box { max-height: 360px; overflow: auto; border: 1px solid #f0f0f0; padding: 12px; border-radius: 8px; }
.preview-group { margin-bottom: 16px; }
.mini-alert { margin-bottom: 8px; }
.add-row { margin-top: 8px; flex-wrap: wrap; }
</style>
