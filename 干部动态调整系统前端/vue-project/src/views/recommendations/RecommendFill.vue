<template>
  <div class="page-shell">
    <a-page-header :title="task?.campaign_name || '党支部优秀干部推荐表'" :sub-title="scopeText" @back="() => router.push({ name: 'RecommendTasks' })" />
    <a-spin :spinning="loading">
      <a-alert v-if="task" type="info" show-icon :message="'填报规则'" :description="task.rules_text" class="notice" />
      <a-card v-if="task" title="党支部优秀干部推荐表" :bordered="false">
        <a-form layout="vertical">
          <a-form-item label="人员类别" required>
            <a-radio-group v-model:value="recommenderCategory" :disabled="readonly">
              <a-radio v-for="item in recommenderCategories" :key="item.key" :value="item.key">{{ item.label }}</a-radio>
            </a-radio-group>
          </a-form-item>
        </a-form>
        <a-row :gutter="16">
          <a-col v-for="category in categories" :key="category.key" :xs="24" :lg="12" :xl="8">
            <a-card size="small" class="post-card" :title="category.label">
              <div class="slot-hint">可推荐 {{ category.slots }} 人；无则留空。{{ category.position_filtered ? '下拉已按相应岗位过滤。' : '未匹配到对应岗位人员，已展示本范围内全部花名册人员。' }}</div>
              <a-form layout="vertical">
                <a-form-item v-for="slot in slotIndexes(category.slots)" :key="`${category.key}-${slot}`" :label="`第 ${slot + 1} 人`">
                  <a-select
                    v-model:value="selections[category.key][slot]"
                    show-search
                    allow-clear
                    option-filter-prop="label"
                    :disabled="readonly"
                    :placeholder="`搜索选择${category.label}`"
                    :options="optionsFor(category, slot)"
                  />
                </a-form-item>
              </a-form>
            </a-card>
          </a-col>
        </a-row>
        <div class="actions">
          <a-space>
            <a-button v-if="!readonly" :loading="saving" @click="saveDraft">保存草稿</a-button>
            <a-button v-if="!readonly" type="primary" :loading="submitting" @click="submit">提交推荐表</a-button>
            <a-tag v-else color="green">已提交</a-tag>
          </a-space>
        </div>
      </a-card>
    </a-spin>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import { recommendationsApi } from '@/api/recommendations'
import { registerModelContextTools } from '@/utils/webmcp'

const route = useRoute()
const router = useRouter()
const task = ref(null)
const loading = ref(false)
const saving = ref(false)
const submitting = ref(false)
const recommenderCategory = ref('')
const selections = ref({})

const readonly = computed(() => task.value?.status === 'SUBMITTED' || !task.value?.is_open)
const recommenderCategories = computed(() => task.value?.recommender_categories || [])
const categories = computed(() => task.value?.candidates?.post_categories || [])
const scopeText = computed(() => {
  if (!task.value) return ''
  const scope = task.value.candidates?.scope_label || task.value.branch_name || task.value.org_unit_name
  return `${scope || '未关联组织'} · 截止 ${task.value.deadline_at ? new Date(task.value.deadline_at).toLocaleString() : '—'}`
})
const slotIndexes = count => Array.from({ length: count }, (_, index) => index)
const selectedIds = computed(() => {
  const ids = new Set()
  Object.values(selections.value).forEach(slots => {
    (slots || []).forEach(id => { if (id) ids.add(id) })
  })
  return ids
})
const optionsFor = (category, slot) => {
  const current = selections.value[category.key]?.[slot]
  return (category.candidates || []).map(item => ({
    value: item.id,
    label: item.label,
    disabled: selectedIds.value.has(item.id) && item.id !== current
  }))
}

const applyTask = data => {
  task.value = data
  recommenderCategory.value = data.recommender_category || ''
  const next = {}
  for (const category of data.candidates?.post_categories || []) {
    next[category.key] = Array.from({ length: category.slots }, () => undefined)
  }
  for (const item of data.nominations || []) {
    if (!next[item.post_category]) next[item.post_category] = []
    next[item.post_category][item.slot_index] = item.roster_id
  }
  selections.value = next
}
const buildNominations = () => {
  const nominations = []
  for (const category of categories.value) {
    (selections.value[category.key] || []).forEach((rosterId, slotIndex) => {
      if (rosterId) nominations.push({ post_category: category.key, slot_index: slotIndex, roster_id: rosterId })
    })
  }
  return nominations
}
const load = async () => {
  loading.value = true
  try {
    applyTask(await recommendationsApi.getTask(route.params.id))
  } catch (error) {
    message.error(error.response?.data?.detail || '推荐表加载失败')
  } finally { loading.value = false }
}
const firstError = payload => {
  if (!payload) return ''
  if (typeof payload === 'string') return payload
  if (Array.isArray(payload)) return firstError(payload[0])
  if (typeof payload === 'object') return firstError(payload.detail || payload.nominations || payload.recommender_category || Object.values(payload)[0])
  return String(payload)
}
const saveDraft = async () => {
  saving.value = true
  try {
    applyTask(await recommendationsApi.saveDraft(route.params.id, {
      recommender_category: recommenderCategory.value || '',
      nominations: buildNominations()
    }))
    message.success('草稿已保存')
  } catch (error) {
    message.error(firstError(error.response?.data) || '保存失败')
  } finally { saving.value = false }
}
const submit = async () => {
  if (!recommenderCategory.value) return message.warning('请选择人员类别')
  submitting.value = true
  try {
    applyTask(await recommendationsApi.submitTask(route.params.id, {
      recommender_category: recommenderCategory.value,
      nominations: buildNominations()
    }))
    message.success('推荐表已提交')
  } catch (error) {
    message.error(firstError(error.response?.data) || '提交失败')
  } finally { submitting.value = false }
}

let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'read_openhrm_recommendation_form', title: '读取优秀干部推荐表',
      description: '读取当前推荐表、候选人范围和已选人员。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute() { if (!task.value) await load(); return { taskId: task.value?.id, campaignName: task.value?.campaign_name, scope: task.value?.candidates?.scope_label, nominations: buildNominations() } }
    },
    {
      name: 'complete_openhrm_recommendation_submit', title: '提交优秀干部推荐表',
      description: '提交当前页面上的推荐人选。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute() { await submit(); return { status: task.value?.status, taskId: task.value?.id } }
    }
  ])
}
onMounted(() => { registerWebMcpTools(); load() })
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>
.page-shell { padding: 8px 16px 24px; }
.notice { margin-bottom: 16px; }
.post-card { margin-bottom: 16px; min-height: 220px; }
.slot-hint { color: #8c8c8c; font-size: 12px; margin-bottom: 8px; }
.actions { margin-top: 8px; }
</style>
