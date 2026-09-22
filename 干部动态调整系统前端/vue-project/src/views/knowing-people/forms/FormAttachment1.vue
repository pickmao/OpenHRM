<template>
  <div>
    <a-form-item label="谈话对象所属党支部">
      <a-input v-model:value="payload.branch_name" :disabled="readonly" />
      <a-tag v-if="(payload.prefill_fields || []).includes('branch_name')" color="blue">组织树</a-tag>
    </a-form-item>
    <a-form-item label="人员类别">
      <a-radio-group v-model:value="payload.personnel_category" :disabled="readonly">
        <a-radio v-for="category in schema.personnel_categories || []" :key="category" :value="category">{{ category }}</a-radio>
      </a-radio-group>
    </a-form-item>
    <div v-if="payload.legacy_overall?.length || payload.legacy_issues?.length" class="legacy-record">
      <strong>历史版本记录（保留原答卷）</strong>
      <div v-for="row in payload.legacy_overall || []" :key="row.key">{{ row.label }}：{{ row.grade || '未填' }}</div>
      <div v-if="payload.legacy_issues?.length">历史问题选项：{{ payload.legacy_issues.map(key => legacyIssueLabels[key] || key).join('、') }}</div>
    </div>
    <h4>1-1 评班子</h4>
    <div v-for="row in payload.overall" :key="row.key" class="overall-row">
      <div class="overall-label">{{ row.label }}</div>
      <a-radio-group v-model:value="row.grade" :disabled="readonly">
        <a-radio v-for="grade in schema.talk_grades || ['好', '较好', '一般', '差']" :key="grade" :value="grade">{{ grade }}</a-radio>
      </a-radio-group>
    </div>
    <a-form-item label="存在的主要问题（可多选）">
      <a-checkbox-group v-model:value="payload.issues" :disabled="readonly" :options="issueOptions" />
    </a-form-item>
    <a-form-item label="其他情况"><a-textarea v-model:value="payload.other" :rows="3" :disabled="readonly" /></a-form-item>
    <h4>1-2 评班子和干部</h4>
    <div class="branch-scores">
      <strong>{{ payload.branch_name || '本党支部' }}班子评价</strong>
      <a-form-item v-for="dim in schema.cadre_talk_dimensions || []" :key="dim.key" :label="dim.label">
        <a-radio-group v-model:value="payload.branch_scores[dim.key]" :disabled="readonly">
          <a-radio v-for="grade in schema.matrix_grades || ['优', '良', '中', '差']" :key="grade" :value="grade">{{ grade }}</a-radio>
        </a-radio-group>
      </a-form-item>
    </div>
    <div class="sheet-wrap">
      <table class="form-sheet">
        <thead>
          <tr>
            <th style="min-width:140px">干部</th>
            <th v-for="dim in schema.cadre_talk_dimensions || []" :key="dim.key"><div>{{ dim.label }}</div><div class="dimension-note">{{ dim.content }}</div></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="target in payload.targets || []" :key="target.id || target.name">
            <td>
              {{ target.name }}
              <div class="muted">{{ target.position || target.department }}</div>
              <a-tag color="blue">花名册</a-tag>
            </td>
            <td v-for="dim in schema.cadre_talk_dimensions || []" :key="dim.key">
              <a-radio-group v-model:value="target.scores[dim.key]" :disabled="readonly">
                <a-radio v-for="grade in schema.matrix_grades || ['优', '良', '中', '差']" :key="grade" :value="grade">{{ grade }}</a-radio>
              </a-radio-group>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ payload: { type: Object, required: true }, schema: { type: Object, default: () => ({}) }, readonly: Boolean })
if (!props.payload.branch_scores) props.payload.branch_scores = {}
const legacyIssueLabels = { weak_politics: '政治意识不够强', shallow_study: '理论学习不深入', poor_centralism: '民主集中制执行不到位', bad_personnel: '选人用人风气不正', weak_responsibility: '担当作为不够', away_from_frontline: '深入一线不够', unclear_thinking: '工作思路不清', poor_decision: '决策科学性不足', loose_rules: '制度执行不严', weak_safety: '抓安全稳定不够有力', poor_unity: '团结协作不够', away_from_masses: '联系群众不够', integrity_risk: '廉洁风险防控不严', formalism: '存在形式主义、官僚主义', other: '其他问题' }
const issueOptions = computed(() => (props.schema.talk_issues || []).map(item => ({ value: item.key, label: item.label })))
</script>

<style scoped>
.legacy-record, .branch-scores { background: #fafafa; padding: 12px; margin-bottom: 16px; }
h4 { margin: 16px 0 8px; }
.overall-row { display: flex; align-items: center; gap: 16px; margin-bottom: 12px; }
.overall-label { min-width: 280px; }
.sheet-wrap { overflow-x: auto; }
.form-sheet { width: 100%; min-width: 860px; border-collapse: collapse; }
.form-sheet th, .form-sheet td { border: 1px solid #d9d9d9; padding: 8px; vertical-align: top; background: #fff; }
.form-sheet th { background: #fafafa; text-align: center; }
.dimension-note { font-weight: normal; font-size: 12px; text-align: left; min-width: 160px; margin-top: 8px; color: #595959; }
.muted { color: #8c8c8c; font-size: 12px; }
:deep(.ant-checkbox-group) { display: flex; flex-direction: column; gap: 6px; }
:deep(.ant-radio-wrapper) { display: block; }
</style>
