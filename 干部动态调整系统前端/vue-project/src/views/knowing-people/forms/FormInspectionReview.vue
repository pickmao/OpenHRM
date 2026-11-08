<template>
  <div>
    <h2 class="sheet-title">考察组谈话及研判记录</h2>
    <div class="sheet-scroll">
      <table class="sheet-grid" style="min-width:1000px">
        <colgroup><col style="width:150px" /><col /><col style="width:150px" /><col /></colgroup>
        <tbody><tr><th>被考察支部</th><td><a-input :value="payload.branch_name" disabled aria-label="被考察支部" /></td><th>材料年度</th><td><a-date-picker v-model:value="payload.material_year" picker="year" value-format="YYYY" :disabled="readonly" aria-label="材料年度" /></td></tr><tr><th>记录日期</th><td><a-date-picker v-model:value="payload.record_date" value-format="YYYY-MM-DD" :disabled="readonly" aria-label="记录日期" /></td><th>考察组或谈话人员</th><td><a-input v-model:value="payload.interviewers" :disabled="readonly" aria-label="考察组或谈话人员" /></td></tr></tbody>
      </table>
      <table class="sheet-grid" style="min-width:1000px;border-top:0">
        <colgroup><col style="width:190px" /><col style="width:34%" /><col /><col /></colgroup>
        <thead><tr><th scope="col">研判对象</th><th scope="col">现场谈话内容</th><th scope="col">能力评价</th><th scope="col">存在不足</th></tr></thead>
        <tbody><tr v-for="(record, index) in payload.records" :key="index" :data-review-index="index"><td class="content-cell"><a-select v-model:value="record.roster_id" :options="targetOptions" show-search option-filter-prop="label" :disabled="readonly" :aria-label="'第' + (index + 1) + '条研判对象'" /><a-button v-if="!readonly" type="text" danger size="small" class="cell-actions" :aria-label="'删除第' + (index + 1) + '条记录'" @click="payload.records.splice(index, 1)">删除记录</a-button></td><td class="content-cell"><a-textarea v-model:value="record.talk_notes" :auto-size="{ minRows: 6, maxRows: 20 }" :disabled="readonly" placeholder="录入现场谈话原文或记录" :aria-label="'第' + (index + 1) + '条现场谈话内容'" /></td><td class="content-cell"><a-textarea v-model:value="record.ability_assessment" :auto-size="{ minRows: 6, maxRows: 16 }" :disabled="readonly" :aria-label="'第' + (index + 1) + '条能力评价'" /></td><td class="content-cell"><a-textarea v-model:value="record.shortcomings" :auto-size="{ minRows: 6, maxRows: 16 }" :disabled="readonly" :aria-label="'第' + (index + 1) + '条存在不足'" /></td></tr><tr v-if="!payload.records.length"><td colspan="4" class="sheet-empty">暂无记录，请增加班子或干部记录。</td></tr></tbody>
      </table>
    </div>
    <a-button v-if="!readonly" class="sheet-add" type="dashed" @click="addRecord">增加班子或干部记录</a-button>
    <p class="sheet-note">每行对应一个班子或一名干部。现场谈话原文保留，能力评价和存在不足按所选对象归集到研判表。</p>
  </div>
</template>
<script setup>
import { computed } from 'vue'
const props = defineProps({ payload: { type: Object, required: true }, schema: { type: Object, default: () => ({}) }, readonly: Boolean })
const targetOptions = computed(() => [{ value: '', label: (props.payload.branch_name || '本支部') + '班子' }, ...(props.schema.roster_people || []).map(person => ({ value: person.id, label: person.name + '（' + person.department + ' · ' + (person.position || '职务未填') + '）' }))])
const addRecord = () => props.payload.records.push({ roster_id: '', talk_notes: '', ability_assessment: '', shortcomings: '' })
</script>
