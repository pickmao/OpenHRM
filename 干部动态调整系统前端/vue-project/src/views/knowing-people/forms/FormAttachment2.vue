<template>
  <div>
    <a-row :gutter="16">
      <a-col :span="8"><a-form-item label="签名"><a-input v-model:value="payload.signature" :disabled="readonly" /></a-form-item></a-col>
      <a-col :span="8"><a-form-item label="自评时间"><a-date-picker v-model:value="payload.self_eval_date" value-format="YYYY-MM-DD" style="width:100%" :disabled="readonly" /></a-form-item></a-col>
      <a-col :span="8"><a-form-item label="单位" required><a-input v-model:value="payload.unit" :disabled="readonly" /><a-tag v-if="prefill('unit')" color="blue">花名册</a-tag></a-form-item></a-col>
      <a-col :span="8"><a-form-item label="姓名" required><a-input v-model:value="payload.name" :disabled="readonly" /><a-tag v-if="prefill('name')" color="blue">花名册</a-tag></a-form-item></a-col>
      <a-col :span="8"><a-form-item label="职务职级"><a-input v-model:value="payload.position_rank" :disabled="readonly" /><a-tag v-if="prefill('position_rank')" color="blue">花名册</a-tag></a-form-item></a-col>
      <a-col :span="8"><a-form-item label="日常居住地"><a-input v-model:value="payload.residence" :disabled="readonly" /><a-tag v-if="prefill('residence')" color="blue">花名册</a-tag></a-form-item></a-col>
      <a-col :span="8">
        <a-form-item label="婚姻状态">
          <a-select v-model:value="payload.marital_status" :disabled="readonly" allow-clear :options="(schema.marital_statuses || []).map(item => ({ value: item, label: item }))" />
        </a-form-item>
      </a-col>
      <a-col :span="16"><a-form-item label="身体情况"><a-input v-model:value="payload.health" :disabled="readonly" /></a-form-item></a-col>
      <a-col :span="8"><a-form-item label="任现职年限"><a-input v-model:value="payload.current_position_years" :disabled="readonly" /><a-tag v-if="prefill('current_position_years')" color="blue">花名册</a-tag></a-form-item></a-col>
      <a-col :span="8"><a-form-item label="机关工作年限"><a-input v-model:value="payload.office_work_years" :disabled="readonly" /></a-form-item></a-col>
      <a-col :span="8"><a-form-item label="监区工作年限"><a-input v-model:value="payload.prison_work_years" :disabled="readonly" /></a-form-item></a-col>
      <a-col :span="24"><a-form-item label="任领导期间主要业务线"><a-textarea v-model:value="payload.main_business_lines" :rows="2" :disabled="readonly" /><a-tag v-if="prefill('main_business_lines')" color="blue">花名册</a-tag></a-form-item></a-col>
      <a-col :span="12"><a-form-item label="近三年奖励"><a-textarea v-model:value="payload.rewards_last_3y" :rows="2" :disabled="readonly" /></a-form-item></a-col>
      <a-col :span="12"><a-form-item label="近三年处理"><a-textarea v-model:value="payload.punishments_last_3y" :rows="2" :disabled="readonly" /></a-form-item></a-col>
    </a-row>
    <div class="sheet-wrap">
      <table class="form-sheet">
        <thead>
          <tr>
            <th style="width:90px">评价维度</th>
            <th>自评要点 / 现实表现</th>
            <th>存在不足</th>
            <th style="width:140px">自评（优/良/中/差）</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in payload.dimensions" :key="row.key">
            <td>{{ row.label }}</td>
            <td><div class="dimension-note">{{ row.content }}</div><a-textarea v-model:value="row.performance" :rows="3" :disabled="readonly" placeholder="现实表现" /></td>
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
    <a-form-item label="整改措施" class="mt"><a-textarea v-model:value="payload.rectification" :rows="3" :disabled="readonly" /></a-form-item>
    <a-form-item label="个人诉求"><a-textarea v-model:value="payload.personal_requests" :rows="2" :disabled="readonly" /></a-form-item>
  </div>
</template>

<script setup>
const props = defineProps({ payload: { type: Object, required: true }, schema: { type: Object, default: () => ({}) }, readonly: Boolean })
const prefill = key => (props.payload.prefill_fields || []).includes(key)
</script>

<style scoped>
.sheet-wrap { overflow-x: auto; margin: 12px 0; }
.form-sheet { width: 100%; border-collapse: collapse; min-width: 720px; }
.form-sheet th, .form-sheet td { border: 1px solid #d9d9d9; padding: 8px; background: #fff; vertical-align: top; }
.form-sheet th { background: #fafafa; text-align: center; }
.dimension-note { font-size: 12px; color: #595959; margin-bottom: 8px; }
.mt { margin-top: 12px; }
</style>
