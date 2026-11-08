<template>
  <a-card title="归集到研判表" size="small" class="collection-card">
    <a-alert v-if="error" :message="error" type="error" show-icon />
    <a-space wrap>
      <span v-if="collection">{{ collection.version_date }} · 班子 {{ collection.leadership_count }} 条 · 干部 {{ collection.cadre_count }} 条</span>
      <span v-else>关联研判期间后，已提交的填报数据将自动更新到两张研判表。</span>
      <a-button v-if="canConfigure" type="primary" :loading="loading" @click="openSettings">{{ collection ? '更新归集设置' : '关联并归集' }}</a-button>
      <a-button v-if="collection" @click="openRecords('LeadershipRecords', collection.leadership_file_id)">打开班子研判</a-button>
      <a-button v-if="collection" @click="openRecords('AssessmentRecords', collection.cadre_file_id)">打开干部研判</a-button>
    </a-space>
    <a-collapse v-if="collection?.warnings?.length" ghost>
      <a-collapse-panel key="warnings" :header="`待核对事项（${collection.warnings.length}）`"><p v-for="item in collection.warnings" :key="item">{{ item }}</p></a-collapse-panel>
    </a-collapse>
    <a-modal v-model:open="settingsOpen" title="设置研判归集" width="760px" :confirm-loading="saving" ok-text="保存并归集" @ok="save">
      <a-form layout="vertical">
        <a-form-item label="研判期间及客观指标统计截止日" required><a-input v-model:value="settings.version_date" type="date" :disabled="Boolean(collection)" /></a-form-item>
        <a-form-item label="班子统计成员默认范围">
          <a-space wrap><span>正式领导</span><a-checkbox v-model:checked="settings.include_team_leaders">包括团队负责人</a-checkbox><a-checkbox v-model:checked="settings.include_designated_leaders">包括内定领导</a-checkbox></a-space>
        </a-form-item>
        <a-form-item v-for="branch in materials?.branches || []" :key="branch.id" :label="`${branch.name}的指定统计名单（可选）`">
          <a-select :value="settings.member_ids[branch.id]" mode="multiple" show-search option-filter-prop="label" allow-clear :options="memberOptions(branch.id)" placeholder="沿用上方默认范围，可指定实际班子成员" @change="value => setMembers(branch.id, value)" />
        </a-form-item>
        <a-form-item label="班子认可率口径">
          <a-select v-model:value="settings.approval_rule" :options="approvalOptions" />
        </a-form-item>
        <a-alert type="info" show-icon message="归集会保留手工修改的研判字段。按材料年度分别写入干事评价；待收齐的分数继续显示缺项。" />
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { knowingPeopleApi } from '@/api/knowingPeople'
import { firstApiError } from '@/utils/apiError'

const props = defineProps({ campaignId: { type: String, required: true }, periodEnd: String })
const router = useRouter()
const collection = ref(null)
const materials = ref(null)
const canConfigure = ref(false)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const settingsOpen = ref(false)
const settings = reactive({ version_date: '', include_team_leaders: true, include_designated_leaders: false, approval_rule: 'UNCONFIRMED', member_ids: {} })
const approvalOptions = [
  { value: 'UNCONFIRMED', label: '待确认，先归集认可度分数' },
  { value: 'RECOGNIZED', label: '认可票 ÷ 四档有效票数' },
  { value: 'RECOGNIZED_AND_BASIC', label: '认可及基本认可票 ÷ 四档有效票数' }
]
let requestId = 0
const load = async () => {
  const current = ++requestId
  loading.value = true
  error.value = ''
  try {
    const result = await knowingPeopleApi.getAssessmentCollection(props.campaignId)
    if (current === requestId) { collection.value = result.collection; canConfigure.value = result.can_configure }
  } catch (failure) {
    if (current === requestId) error.value = firstApiError(failure.response?.data) || '归集状态加载失败'
  } finally { if (current === requestId) loading.value = false }
}
watch(() => props.campaignId, () => { collection.value = null; settingsOpen.value = false; load() }, { immediate: true })
const openSettings = async () => {
  try {
    materials.value = await knowingPeopleApi.getMaterials(props.campaignId)
    Object.assign(settings, { version_date: props.periodEnd || '', include_team_leaders: true, include_designated_leaders: false, approval_rule: 'UNCONFIRMED', member_ids: {} }, collection.value || {})
    settings.member_ids = JSON.parse(JSON.stringify(settings.member_ids || {}))
    settingsOpen.value = true
  } catch (failure) { message.error(firstApiError(failure.response?.data) || '归集设置加载失败') }
}
const memberOptions = branchId => (materials.value?.roster_people || []).filter(row => row.branch_id === branchId).map(row => ({ value: row.id, label: `${row.name}（${row.position || row.department}）` }))
const setMembers = (branchId, values) => {
  if (values.length) settings.member_ids[branchId] = values
  else delete settings.member_ids[branchId]
}
const save = async () => {
  if (!settings.version_date) return message.warning('请选择研判期间')
  saving.value = true
  try {
    collection.value = await knowingPeopleApi.collectAssessments(props.campaignId, {
      version_date: settings.version_date, include_team_leaders: settings.include_team_leaders,
      include_designated_leaders: settings.include_designated_leaders,
      approval_rule: settings.approval_rule, member_ids: settings.member_ids
    })
    settingsOpen.value = false
    message.success('已归集到班子和干部研判表，后续提交及退回会自动更新')
  } catch (failure) { message.error(firstApiError(failure.response?.data) || '归集失败') }
  finally { saving.value = false }
}
const openRecords = (name, file) => router.push({ name, query: { file } })
defineExpose({ refresh: load })
</script>

<style scoped>
.collection-card { margin-bottom: 16px; }
</style>
