<template>
  <div>
    <a-alert type="info" show-icon message="请填写本次考察年度内每段任职经历及重点工作，具体至年月，说明承担的任务和作用；承担角色可多选。" style="margin-bottom:16px" />
    <a-row :gutter="16">
      <a-col :span="8"><a-form-item label="姓名" required><a-input v-model:value="payload.name" :disabled="readonly" /><a-tag v-if="prefill('name')" color="blue">花名册</a-tag></a-form-item></a-col>
      <a-col :span="8"><a-form-item label="性别"><a-input v-model:value="payload.gender" :disabled="readonly" /><a-tag v-if="prefill('gender')" color="blue">花名册</a-tag></a-form-item></a-col>
      <a-col :span="8"><a-form-item label="出生年月"><a-input v-model:value="payload.birth_date" :disabled="readonly" placeholder="YYYY-MM" /><a-tag v-if="prefill('birth_date')" color="blue">花名册</a-tag></a-form-item></a-col>
      <a-col :span="8"><a-form-item label="现部门及职务"><a-input v-model:value="payload.department_position" :disabled="readonly" /><a-tag v-if="prefill('department_position')" color="blue">花名册</a-tag></a-form-item></a-col>
      <a-col :span="8"><a-form-item label="任现职务时间"><a-input v-model:value="payload.current_position_date" :disabled="readonly" /><a-tag v-if="prefill('current_position_date')" color="blue">花名册</a-tag></a-form-item></a-col>
      <a-col :span="8"><a-form-item label="政治面貌"><a-input v-model:value="payload.political_status" :disabled="readonly" /><a-tag v-if="prefill('political_status')" color="blue">花名册</a-tag></a-form-item></a-col>
    </a-row>
    <div v-for="(row, index) in payload.items" :key="index" class="work-block">
      <div class="work-title">第 {{ index + 1 }} 条 <a-button v-if="!readonly" type="link" danger @click="remove(index)">删除</a-button></div>
      <a-form-item label="任职经历"><a-textarea v-model:value="row.experience" :rows="2" :disabled="readonly" /></a-form-item>
      <a-form-item label="重点工作" required><a-textarea v-model:value="row.key_work" :rows="2" :disabled="readonly" /></a-form-item>
      <a-form-item label="承担角色">
        <a-checkbox-group v-model:value="row.roles" :disabled="readonly" :options="schema.roles || ['主导者', '协助者', '执行者']" />
      </a-form-item>
      <a-form-item label="事情详细情况" required><a-textarea v-model:value="row.details" :rows="4" :disabled="readonly" /></a-form-item>
    </div>
    <a-button v-if="!readonly" type="dashed" block @click="add">新增一条重点工作</a-button>
    <a-row :gutter="16" style="margin-top:16px">
      <a-col :span="12"><a-form-item label="个人签名"><a-input v-model:value="payload.signature" :disabled="readonly" /></a-form-item></a-col>
      <a-col :span="12"><a-form-item label="填写时间"><a-date-picker v-model:value="payload.fill_date" value-format="YYYY-MM-DD" :disabled="readonly" /></a-form-item></a-col>
    </a-row>
  </div>
</template>

<script setup>
const props = defineProps({ payload: { type: Object, required: true }, schema: { type: Object, default: () => ({}) }, readonly: Boolean })
const prefill = key => (props.payload.prefill_fields || []).includes(key)
const add = () => { props.payload.items = [...(props.payload.items || []), { experience: '', key_work: '', roles: [], details: '' }] }
const remove = index => { props.payload.items.splice(index, 1) }
</script>

<style scoped>
.work-block { border: 1px solid #f0f0f0; padding: 12px 16px; margin-bottom: 12px; border-radius: 8px; background: #fafafa; }
.work-title { font-weight: 600; margin-bottom: 8px; }
</style>
