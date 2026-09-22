<template>
  <div>
    <a-row :gutter="16">
      <a-col :span="12"><a-form-item label="党支部（盖章位可用单位名）" required><a-input v-model:value="payload.branch_name" :disabled="readonly" /><a-tag v-if="prefill('branch_name')" color="blue">组织树</a-tag></a-form-item></a-col>
      <a-col :span="12"><a-form-item label="评价时间"><a-date-picker v-model:value="payload.eval_date" value-format="YYYY-MM-DD" style="width:100%" :disabled="readonly" /></a-form-item></a-col>
      <a-col :span="6"><a-form-item label="监区/部门领导现有人数"><a-input-number v-model:value="payload.leadership_current" :min="0" style="width:100%" :disabled="readonly" /></a-form-item></a-col>
      <a-col :span="6"><a-form-item label="领导空缺人数"><a-input-number v-model:value="payload.leadership_vacancy" :min="0" style="width:100%" :disabled="readonly" /></a-form-item></a-col>
      <a-col :span="6"><a-form-item label="工作团队负责人现有"><a-input-number v-model:value="payload.team_leader_current" :min="0" style="width:100%" :disabled="readonly" /></a-form-item></a-col>
      <a-col :span="6"><a-form-item label="团队负责人空缺"><a-input-number v-model:value="payload.team_leader_vacancy" :min="0" style="width:100%" :disabled="readonly" /></a-form-item></a-col>
      <a-col :span="24">
        <a-form-item label="班子阅历结构（人）">
          <a-space wrap>
            <label v-for="item in experienceFields" :key="item.key">{{ item.label }}
              <a-input-number v-model:value="payload.experience_counts[item.key]" :min="0" :precision="0" :disabled="readonly" />
            </label>
          </a-space>
          <div v-if="payload.experience_structure" class="muted">历史单选记录：{{ payload.experience_structure }}（请按原表补充人数）</div>
        </a-form-item>
      </a-col>
    </a-row>
    <div class="sheet-wrap">
      <table class="form-sheet">
        <thead>
          <tr>
            <th style="width:110px">类别</th>
            <th style="width:110px">评价项目</th>
            <th>内容 / 评价要点</th>
            <th>现实表现</th>
            <th>存在不足</th>
            <th style="width:130px">评价（优/良/中/差）</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in payload.items" :key="row.key">
            <td>{{ row.category }}</td>
            <td>{{ row.label }}</td>
            <td>
              <div class="muted">{{ row.content }}</div>

            </td>
            <td><a-textarea v-model:value="row.performance" :rows="3" :disabled="readonly" /></td>
            <td><a-textarea v-model:value="row.shortcomings" :rows="3" :disabled="readonly" /></td>
            <td>
              <a-radio-group v-model:value="row.grade" :disabled="readonly">
                <a-radio v-for="grade in schema.self_eval_grades || ['优', '良', '中', '差']" :key="grade" :value="grade">{{ grade }}</a-radio>
              </a-radio-group>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <a-form-item label="整改措施"><a-textarea v-model:value="payload.rectification" :rows="3" :disabled="readonly" /></a-form-item>
    <a-form-item label="班子诉求"><a-textarea v-model:value="payload.team_requests" :rows="3" :disabled="readonly" /></a-form-item>
    <a-form-item label="是否需要调整"><a-radio-group v-model:value="payload.adjustment_needed" :disabled="readonly"><a-radio value="是">是</a-radio><a-radio value="否">否</a-radio></a-radio-group></a-form-item>
    <a-form-item label="调整建议"><a-textarea v-model:value="payload.adjustment_suggestion" :rows="3" :disabled="readonly" /></a-form-item>
  </div>
</template>

<script setup>
const props = defineProps({ payload: { type: Object, required: true }, schema: { type: Object, default: () => ({}) }, readonly: Boolean })
if (!props.payload.experience_counts) props.payload.experience_counts = { office: null, balanced: null, prison: null }
const experienceFields = [{ key: 'office', label: '长期在机关' }, { key: 'balanced', label: '相对均衡' }, { key: 'prison', label: '长期在监区' }]
const prefill = key => (props.payload.prefill_fields || []).includes(key)
</script>

<style scoped>
.sheet-wrap { overflow-x: auto; }
.form-sheet { width: 100%; min-width: 980px; border-collapse: collapse; }
.form-sheet th, .form-sheet td { border: 1px solid #d9d9d9; padding: 8px; vertical-align: top; background: #fff; }
.form-sheet th { background: #fafafa; text-align: center; }
.muted { color: #595959; font-size: 12px; margin-bottom: 6px; }
</style>
