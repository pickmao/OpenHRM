<template>
  <div>
    <a-row :gutter="16">
      <a-col :span="12"><a-form-item label="被考察支部"><a-input :value="payload.branch_name" disabled /></a-form-item></a-col>
      <a-col :span="12"><a-form-item label="材料年度" required><a-date-picker v-model:value="payload.material_year" picker="year" value-format="YYYY" :disabled="readonly" /></a-form-item></a-col>
      <a-col :span="12"><a-form-item label="记录日期" required><a-date-picker v-model:value="payload.record_date" value-format="YYYY-MM-DD" :disabled="readonly" /></a-form-item></a-col>
      <a-col :span="12"><a-form-item label="考察组或谈话人员" required><a-input v-model:value="payload.interviewers" :disabled="readonly" /></a-form-item></a-col>
    </a-row>
    <a-card v-for="(record, index) in payload.records" :key="index" :title="`记录 ${index + 1}`" class="review-record">
      <template #extra><a-button v-if="!readonly" type="link" danger @click="payload.records.splice(index, 1)">删除记录</a-button></template>
      <a-form-item label="研判对象" required>
        <a-select v-model:value="record.roster_id" :options="targetOptions" show-search option-filter-prop="label" :disabled="readonly" style="width:100%" />
      </a-form-item>
      <a-form-item label="现场谈话内容"><a-textarea v-model:value="record.talk_notes" :rows="5" :disabled="readonly" placeholder="录入现场谈话原文或记录" /></a-form-item>
      <a-form-item label="能力评价"><a-textarea v-model:value="record.ability_assessment" :rows="3" :disabled="readonly" /></a-form-item>
      <a-form-item label="存在不足"><a-textarea v-model:value="record.shortcomings" :rows="3" :disabled="readonly" /></a-form-item>
    </a-card>
    <a-button v-if="!readonly" type="dashed" block @click="addRecord">增加班子或干部记录</a-button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ payload: { type: Object, required: true }, schema: { type: Object, default: () => ({}) }, readonly: Boolean })
const targetOptions = computed(() => [
  { value: '', label: `${props.payload.branch_name || '本支部'}班子` },
  ...(props.schema.roster_people || []).map(person => ({ value: person.id, label: `${person.name}（${person.department} · ${person.position || '职务未填'}）` }))
])
const addRecord = () => props.payload.records.push({ roster_id: '', talk_notes: '', ability_assessment: '', shortcomings: '' })
</script>

<style scoped>
.review-record { margin-bottom: 16px; }
</style>
