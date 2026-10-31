<template>
  <div>
    <a-alert v-if="!(payload.targets || []).length && formType !== 'ATTACHMENT_6_2'" type="warning" show-icon message="暂无预填评价对象，请联系管理员检查花名册或组织树。" class="notice" />
    <a-form-item v-if="formType === 'ATTACHMENT_6_2'" label="评价党支部">
      <a-input v-model:value="payload.branch_name" :disabled="readonly" />
      <a-tag v-if="(payload.prefill_fields || []).includes('branch_name')" color="blue">组织树</a-tag>
    </a-form-item>
    <div class="sheet-wrap">
      <table class="form-sheet">
        <thead>
          <tr>
            <th style="min-width:140px">{{ targetLabel }}</th>
            <th v-if="showPosition" style="min-width:140px">职务职级</th>
            <th v-for="dim in dimensions" :key="dim.key"><div>{{ dim.label }}</div><div class="dimension-note">{{ dim.content }}</div></th>
            <th v-if="showRecognition">工作认可度</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="target in rows" :key="target.id || target.name">
            <td>
              {{ target.name }}
              <div class="muted">{{ target.department }}</div>
              <a-tag color="blue">花名册/组织树</a-tag>
            </td>
            <td v-if="showPosition">{{ target.position || '—' }}</td>
            <td v-for="dim in dimensions" :key="dim.key">
              <a-radio-group v-model:value="target.scores[dim.key]" :disabled="readonly">
                <a-radio v-for="grade in schema.matrix_grades || ['优', '良', '中', '差']" :key="grade" :value="grade">{{ grade }}</a-radio>
              </a-radio-group>
            </td>
            <td v-if="showRecognition">
              <a-radio-group v-if="formType === 'ATTACHMENT_6_2'" v-model:value="payload.recognition" :disabled="readonly">
                <a-radio v-for="option in recognitionOptions" :key="option" :value="option">{{ option }}</a-radio>
              </a-radio-group>
              <a-radio-group v-else v-model:value="target.recognition" :disabled="readonly">
                <a-radio v-for="option in recognitionOptions" :key="option" :value="option">{{ option }}</a-radio>
              </a-radio-group>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <template v-if="showOpenQuestions">
      <a-form-item label="现实表现">
        <a-textarea v-model:value="payload.performance" :rows="3" :disabled="readonly" />
      </a-form-item>
      <a-form-item label="存在不足">
        <a-textarea v-model:value="payload.shortcomings" :rows="3" :disabled="readonly" />
      </a-form-item>
      <a-form-item label="需要反映的其他情况">
        <a-textarea v-model:value="payload.other_issues" :rows="3" :disabled="readonly" />
      </a-form-item>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  payload: { type: Object, required: true },
  schema: { type: Object, default: () => ({}) },
  readonly: Boolean,
  formType: { type: String, required: true }
})

const dimensions = computed(() => props.schema.team_dimensions || [])
const showRecognition = computed(() => ['ATTACHMENT_6_2', 'ATTACHMENT_7_4'].includes(props.formType))
const recognitionOptions = computed(() => props.schema.recognition_options || ['认可', '基本认可', '不认可', '不了解'])
const showPosition = computed(() => ['ATTACHMENT_7_1', 'ATTACHMENT_7_2', 'ATTACHMENT_7_3', 'ATTACHMENT_7_4'].includes(props.formType))
const showOpenQuestions = computed(() => [
  'ATTACHMENT_6_1',
  'ATTACHMENT_6_2',
  'ATTACHMENT_7_1',
  'ATTACHMENT_7_2',
  'ATTACHMENT_7_3',
  'ATTACHMENT_7_4',
].includes(props.formType))
const targetLabel = computed(() => (props.formType.startsWith('ATTACHMENT_6') ? '党支部' : '评价对象'))
const rows = computed(() => {
  if (props.formType === 'ATTACHMENT_6_2') {
    if (props.payload.targets?.length) return props.payload.targets
    if (!props.payload.scores) props.payload.scores = {}
    return [{
      id: 'self-branch',
      name: props.payload.branch_name || '本支部',
      department: props.payload.branch_name || '',
      scores: props.payload.scores
    }]
  }
  return props.payload.targets || []
})
</script>

<style scoped>
.notice { margin-bottom: 12px; }
.sheet-wrap { overflow-x: auto; }
.form-sheet { width: 100%; min-width: 960px; border-collapse: collapse; }
.form-sheet th, .form-sheet td { border: 1px solid #d9d9d9; padding: 8px; vertical-align: top; background: #fff; }
.form-sheet th { background: #fafafa; text-align: center; white-space: nowrap; }
.dimension-note { white-space: normal; min-width: 180px; font-weight: normal; font-size: 12px; text-align: left; margin-top: 8px; color: #595959; }
.muted { color: #8c8c8c; font-size: 12px; }
:deep(.ant-radio-wrapper) { display: block; margin-right: 0; }
</style>
