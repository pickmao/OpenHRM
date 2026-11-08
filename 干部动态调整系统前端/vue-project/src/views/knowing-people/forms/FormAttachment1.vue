<template>
  <div>
    <div class="sheet-attachment">附件1-1</div><h2 class="sheet-title">近距离考察干部谈话研判测评表<br />（中层领导班子）</h2>
    <div class="sheet-meta"><label><span>所在党支部：</span><a-input v-model:value="payload.branch_name" :disabled="readonly" aria-label="谈话对象所属党支部" /></label></div>
    <div v-if="payload.legacy_overall?.length || payload.legacy_issues?.length" class="legacy-record"><strong>历史版本记录</strong><div v-for="row in payload.legacy_overall || []" :key="row.key">{{ row.label }}：{{ row.grade || '未填' }}</div><div v-if="payload.legacy_issues?.length">历史问题选项：{{ payload.legacy_issues.map(key => legacyIssueLabels[key] || key).join('、') }}</div></div>
    <div class="sheet-scroll">
      <table class="sheet-grid" style="min-width:820px">
        <colgroup><col /><col v-for="grade in talkGrades" :key="grade" style="width:70px" /></colgroup>
        <thead><tr><th rowspan="2" scope="col">评价内容</th><th :colspan="talkGrades.length" scope="colgroup">评价结果</th></tr><tr><th v-for="grade in talkGrades" :key="grade" scope="col">{{ grade }}</th></tr></thead>
        <tbody><tr v-for="row in payload.overall" :key="row.key"><th scope="row" class="content-cell">{{ row.label }}</th><td v-for="grade in talkGrades" :key="grade" class="choice-cell"><label class="choice-label"><input v-model="row.grade" type="radio" class="sheet-radio" :name="groupId + '-' + row.key" :value="grade" :disabled="readonly" :aria-label="row.label + ' ' + grade" /></label></td></tr>
          <tr><th :colspan="talkGrades.length + 1" class="content-cell">4．您认为本部门（监区）存在的主要问题是什么？（可多选，无问题可不选）</th></tr>
          <tr v-for="item in schema.talk_issues || []" :key="item.key"><td :colspan="talkGrades.length" class="content-cell"><label :for="groupId + '-issue-' + item.key">{{ item.label }}</label></td><td class="choice-cell"><input :id="groupId + '-issue-' + item.key" v-model="payload.issues" type="checkbox" class="sheet-checkbox" :value="item.key" :disabled="readonly" :aria-label="item.label" /></td></tr>
          <tr><td :colspan="talkGrades.length + 1" class="content-cell"><label class="cell-label">其他情况</label><a-textarea v-model:value="payload.other" :auto-size="{ minRows: 3, maxRows: 14 }" :disabled="readonly" aria-label="其他情况" /></td></tr>
        </tbody>
      </table>
    </div>
    <div class="sheet-attachment" style="margin-top:28px">附件1-2</div><h2 class="sheet-title">近距离考察干部谈话研判测评表<br />（中层领导班子和领导干部）</h2>
    <div class="sheet-meta"><span>人员类别：</span><a-radio-group v-model:value="payload.personnel_category" :disabled="readonly"><a-radio v-for="category in schema.personnel_categories || []" :key="category" :value="category">{{ category }}</a-radio></a-radio-group></div>
    <ScoreMatrixTable :rows="branchRows" :dimensions="schema.cadre_talk_dimensions || []" :grades="schema.matrix_grades" identity-label="党支部" :readonly="readonly" />
    <h3 class="sheet-subtitle">领导干部评价</h3>
    <ScoreMatrixTable :rows="payload.targets || []" :dimensions="schema.cadre_talk_dimensions || []" :grades="schema.matrix_grades" show-position :readonly="readonly" />
    <p class="sheet-note">每个评价项目选择一个档次，班子和干部评价分别填写。</p>
  </div>
</template>
<script setup>
import { computed, useId } from 'vue'
import ScoreMatrixTable from './ScoreMatrixTable.vue'
const props = defineProps({ payload: { type: Object, required: true }, schema: { type: Object, default: () => ({}) }, readonly: Boolean })
const groupId = useId()
if (!props.payload.branch_scores) props.payload.branch_scores = {}
const talkGrades = computed(() => props.schema.talk_grades || ['好', '较好', '一般', '差'])
const branchRows = computed(() => [{ id: 'branch', name: props.payload.branch_name || '本党支部', scores: props.payload.branch_scores }])
const legacyIssueLabels = { weak_politics: '政治意识不够强', shallow_study: '理论学习不深入', poor_centralism: '民主集中制执行不到位', bad_personnel: '选人用人风气不正', weak_responsibility: '担当作为不够', away_from_frontline: '深入一线不够', unclear_thinking: '工作思路不清', poor_decision: '决策科学性不足', loose_rules: '制度执行不严', weak_safety: '抓安全稳定不够有力', poor_unity: '团结协作不够', away_from_masses: '联系群众不够', integrity_risk: '廉洁风险防控不严', formalism: '存在形式主义、官僚主义', other: '其他问题' }
</script>
