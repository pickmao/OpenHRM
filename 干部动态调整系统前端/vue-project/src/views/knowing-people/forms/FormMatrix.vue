<template>
  <div>
    <div class="sheet-attachment">{{ attachmentNumber }}</div>
    <h2 class="sheet-title">{{ title }}</h2>
    <div class="sheet-meta"><span>人员类别：{{ fillerRole || '按下发任务指定' }}</span><label v-if="formType === 'ATTACHMENT_6_2'"><span>评价党支部：</span><a-input v-model:value="payload.branch_name" :disabled="readonly" aria-label="评价党支部" /></label></div>
    <ScoreMatrixTable :rows="rows" :dimensions="schema.team_dimensions || []" :grades="schema.matrix_grades" :identity-label="showPosition ? '姓名' : '党支部'" :show-position="showPosition" :show-recognition="showRecognition" :recognition-options="schema.recognition_options" :recognition-owner="formType === 'ATTACHMENT_6_2' ? payload : null" :readonly="readonly">
      <template #footer="{ identityColumns, scoreColumns }"><tr v-for="field in openFields" :key="field.key"><th :colspan="identityColumns" scope="row">{{ field.label }}</th><td :colspan="scoreColumns" class="content-cell"><a-textarea v-model:value="payload[field.key]" :auto-size="{ minRows: 2, maxRows: 10 }" :disabled="readonly" :aria-label="field.label" /></td></tr></template>
    </ScoreMatrixTable>
    <p class="sheet-note">请在每项评价对应的档次下选择一项。表格较宽时可横向滚动，或使用页面右上角的“宽屏填写”。</p>
  </div>
</template>
<script setup>
import { computed } from 'vue'
import ScoreMatrixTable from './ScoreMatrixTable.vue'
const props = defineProps({ payload: { type: Object, required: true }, schema: { type: Object, default: () => ({}) }, readonly: Boolean, formType: { type: String, required: true }, fillerRole: { type: String, default: '' } })
const showRecognition = computed(() => ['ATTACHMENT_6_2', 'ATTACHMENT_7_4'].includes(props.formType))
const showPosition = computed(() => props.formType.startsWith('ATTACHMENT_7'))
const attachmentNumber = computed(() => '附件' + props.formType.replace('ATTACHMENT_', '').replaceAll('_', '-'))
const title = computed(() => ({ ATTACHMENT_6_1: '近距离考察干部中层领导班子评价研判测评表', ATTACHMENT_6_2: '近距离考察干部中层领导班子评价研判测评表', ATTACHMENT_7_1: '近距离考察干部中层领导干部评价研判测评表（正职领导）', ATTACHMENT_7_2: '近距离考察干部中层领导干部评价研判测评表（副职领导）', ATTACHMENT_7_3: '近距离考察中层领导干部评价研判测评表（工作团队负责人）', ATTACHMENT_7_4: '近距离考察干部评价研判测评表（党支部全体干部）' })[props.formType])
const rows = computed(() => {
  if (props.formType === 'ATTACHMENT_6_2') {
    if (!props.payload.scores) props.payload.scores = {}
    return [{ id: 'self-branch', name: props.payload.branch_name || '本支部', scores: props.payload.scores }]
  }
  return props.payload.targets || []
})
const openFields = [{ key: 'performance', label: '现实表现' }, { key: 'shortcomings', label: '存在不足' }, { key: 'other_issues', label: '需要反映的其他情况' }]
</script>
