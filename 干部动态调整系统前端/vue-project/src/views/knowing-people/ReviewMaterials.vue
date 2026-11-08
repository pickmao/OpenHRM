<template>
  <a-card title="研判材料汇总" class="materials-card" :loading="loading">
    <a-alert v-if="error" type="error" show-icon :message="error" class="notice" />
    <template v-if="materials">
      <a-space wrap class="notice">
        <a-select v-model:value="branchId" allow-clear :options="branchOptions" placeholder="全部填报支部" style="min-width:220px" />
        <a-select v-model:value="year" allow-clear :options="yearOptions" placeholder="全部材料年度" style="width:160px" />
        <a-button @click="load">刷新材料</a-button>
      </a-space>
      <a-alert type="info" show-icon class="notice" :message="`已提交 ${materials.submitted_count} 份，待提交 ${materials.pending_count} 份。下方归集已提交内容；退回后会移出。花名册信息取自当前人员库。`" />
      <a-tabs>
        <a-tab-pane key="stories" tab="年度述事">
          <a-empty v-if="!stories.length" description="尚无已提交的支部述事材料" />
          <a-collapse v-else>
            <a-collapse-panel v-for="story in stories" :key="story.id" :header="`${story.year || '年度待补充'} · ${story.branch_name} · ${story.title || '工作名称未填'}`">
              <p v-if="story.year_source !== '填报年度'" class="year-note">年度依据为{{ story.year_source }}，核对历史材料时请确认实际发生年度。</p>
              <p class="material-text">{{ story.description || '简要表述未填' }}</p>
              <a-table :data-source="story.people" :columns="peopleColumns" :pagination="false" size="small" :row-key="(_, index) => index">
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'person'">{{ record.name }} <a-tag v-if="!record.roster_id" color="orange">待关联花名册</a-tag></template>
                </template>
              </a-table>
              <div class="source-line">附件5 · {{ story.assignee_name }} · {{ formatDate(story.submitted_at) }}</div>
              <a-button v-if="materials.can_view_source" type="link" @click="openSource(story)">查看原表</a-button>
            </a-collapse-panel>
          </a-collapse>
        </a-tab-pane>
        <a-tab-pane key="reviews" tab="谈话及研判记录">
          <a-table :data-source="reviews" :columns="reviewColumns" row-key="id" :scroll="{ x: 1500 }" :pagination="{ pageSize: 10 }" size="small">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'target'">{{ record.name }}<div class="source-line">{{ record.roster_id ? '干部' : '班子' }} · {{ record.branch_name }}</div></template>
              <template v-else-if="column.key === 'source'"><a-button v-if="materials.can_view_source" type="link" @click="openSource(record)">查看原表</a-button></template>
            </template>
          </a-table>
        </a-tab-pane>
        <a-tab-pane key="sources" tab="其他原表内容">
          <a-empty v-if="!sources.length" description="尚无已提交的其他文字材料" />
          <a-collapse v-else>
            <a-collapse-panel v-for="source in sources" :key="source.source_task_id" :header="`${source.form_label} · ${source.assignee_name} · ${source.branch_name}`">
              <p v-if="source.scope_names.length" class="source-line">该原表涉及的对象为{{ source.scope_names.join('、') }}。整表意见需结合原表核对具体对象。</p>
              <dl v-for="(field, index) in source.fields" :key="index">
                <dt>{{ field.label }}</dt><dd class="material-text">{{ field.text || '未填' }}</dd>
              </dl>
              <a-button v-if="materials.can_view_source" type="link" @click="openSource(source)">查看原表</a-button>
            </a-collapse-panel>
          </a-collapse>
        </a-tab-pane>
        <a-tab-pane key="roster" tab="花名册基础信息">
          <p class="source-line">{{ materials.roster_source }}。可核对成员的年龄、最高学历、任现职时间。班子成员范围及统计截止日按本次考察要求确认。</p>
          <a-table :data-source="rosterPeople" :columns="rosterColumns" :row-key="row => `${row.branch_id}-${row.id}`" :scroll="{ x: 1200 }" :pagination="{ pageSize: 10 }" size="small" />
        </a-tab-pane>
      </a-tabs>
    </template>
    <a-button v-else-if="error" @click="load">重试</a-button>
  </a-card>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { knowingPeopleApi } from '@/api/knowingPeople'
import { useRouter } from 'vue-router'

const props = defineProps({ campaignId: { type: String, required: true } })
const router = useRouter()
const openSource = row => router.push({ name: 'KnowingPeopleFill', params: { id: row.source_task_id } })
const materials = ref(null)
const loading = ref(false)
const error = ref('')
const branchId = ref(undefined)
const year = ref(undefined)
let requestId = 0
const load = async () => {
  const current = ++requestId
  loading.value = true
  error.value = ''
  try {
    const data = await knowingPeopleApi.getMaterials(props.campaignId)
    if (current === requestId) materials.value = data
  } catch (failure) {
    if (current === requestId) {
      materials.value = null
      error.value = failure.response?.data?.detail || '研判材料加载失败'
    }
  } finally {
    if (current === requestId) loading.value = false
  }
}
watch(() => props.campaignId, () => { materials.value = null; branchId.value = undefined; year.value = undefined; load() }, { immediate: true })
defineExpose({ refresh: load })
const branchOptions = computed(() => (materials.value?.branches || []).map(row => ({ value: row.id, label: row.name })))
const yearOptions = computed(() => [...new Set([...(materials.value?.stories || []), ...(materials.value?.reviews || [])].map(row => row.year).filter(Boolean))].sort().reverse().map(value => ({ value, label: `${value}年` })))
const byBranch = row => !branchId.value || row.branch_id === branchId.value
const byYear = row => !year.value || row.year === year.value
const stories = computed(() => (materials.value?.stories || []).filter(row => byBranch(row) && byYear(row)))
const reviews = computed(() => (materials.value?.reviews || []).filter(row => byBranch(row) && byYear(row)))
const sources = computed(() => (materials.value?.sources || []).filter(byBranch))
const rosterPeople = computed(() => (materials.value?.roster_people || []).filter(byBranch))
const formatDate = value => value ? new Date(value).toLocaleString() : '提交时间未记录'
const peopleColumns = [
  { title: '具体人员', key: 'person', width: 180 },
  { title: '部门', dataIndex: 'department', width: 160 },
  { title: '承担角色', dataIndex: 'roles', width: 180, customRender: ({ text }) => (text || []).join('、') },
  { title: '具体任务和作用发挥', dataIndex: 'task_and_role', className: 'material-text' }
]
const reviewColumns = [
  { title: '对象', key: 'target', width: 180 },
  { title: '年度', dataIndex: 'year', width: 80 },
  { title: '记录日期', dataIndex: 'record_date', width: 120 },
  { title: '考察组或谈话人员', dataIndex: 'interviewers', width: 180 },
  { title: '现场谈话内容', dataIndex: 'talk_notes', width: 350, className: 'material-text' },
  { title: '能力评价', dataIndex: 'ability_assessment', width: 250, className: 'material-text' },
  { title: '存在不足', dataIndex: 'shortcomings', width: 250, className: 'material-text' },
  { title: '来源', key: 'source', width: 110 }
]
const rosterColumns = [
  { title: '姓名', dataIndex: 'name', width: 100 },
  { title: '部门', dataIndex: 'department', width: 140 },
  { title: '职务', dataIndex: 'position', width: 160 },
  { title: '职务类别', dataIndex: 'position_category', width: 130 },
  { title: '年龄', dataIndex: 'age', width: 80 },
  { title: '出生年月', dataIndex: 'birth_date', width: 120 },
  { title: '最高学历', dataIndex: 'highest_education', width: 140 },
  { title: '任现职年限', dataIndex: 'current_position_years', width: 100 },
  { title: '任现职时间', dataIndex: 'current_position_date', width: 120 }
]
</script>

<style scoped>
.materials-card { margin-bottom: 20px; }
.notice { margin-bottom: 16px; }
.material-text { white-space: pre-wrap; overflow-wrap: anywhere; }
.source-line { color: #595959; font-size: 12px; margin-top: 10px; }
.year-note { color: #874d00; }
dt { font-weight: 600; }
dd { margin: 4px 0 12px; }
</style>
