<template>
  <div>
    <div class="sheet-attachment">附件2</div><h2 class="sheet-title">近距离考察干部自评表</h2>
    <div class="sheet-meta"><label><span>签名：</span><a-input v-model:value="payload.signature" :disabled="readonly" aria-label="签名" /></label><label><span>自评时间：</span><a-date-picker v-model:value="payload.self_eval_date" value-format="YYYY-MM-DD" :disabled="readonly" aria-label="自评时间" /></label></div>
    <div class="sheet-scroll">
      <table class="sheet-grid" style="min-width:1000px">
        <colgroup><col style="width:42px" /><col style="width:112px" /><col /><col style="width:110px" /><col /><col style="width:120px" /><col /></colgroup>
        <tbody>
          <tr><th rowspan="5" class="section-label vertical-label">个人基本情况</th><th>单位</th><td><a-input v-model:value="payload.unit" :disabled="readonly" aria-label="单位" /></td><th>姓名</th><td><a-input v-model:value="payload.name" :disabled="readonly" aria-label="姓名" /></td><th>职务职级</th><td><a-input v-model:value="payload.position_rank" :disabled="readonly" aria-label="职务职级" /></td></tr>
          <tr><th>日常居住地</th><td><a-input v-model:value="payload.residence" :disabled="readonly" aria-label="日常居住地" /></td><th>婚姻状态</th><td><a-select v-model:value="payload.marital_status" :disabled="readonly" allow-clear :options="(schema.marital_statuses || []).map(item => ({ value: item, label: item }))" aria-label="婚姻状态" /></td><th>身体情况</th><td><a-input v-model:value="payload.health" :disabled="readonly" aria-label="身体情况" /></td></tr>
          <tr><th>任现职年限</th><td><a-input v-model:value="payload.current_position_years" :disabled="readonly" aria-label="任现职年限" /></td><th>机关工作年限</th><td><a-input v-model:value="payload.office_work_years" :disabled="readonly" aria-label="机关工作年限" /></td><th>监区工作年限</th><td><a-input v-model:value="payload.prison_work_years" :disabled="readonly" aria-label="监区工作年限" /></td></tr>
          <tr><th>任领导期间主要从事的业务线</th><td colspan="5" class="content-cell"><a-textarea v-model:value="payload.main_business_lines" :auto-size="{ minRows: 2, maxRows: 8 }" :disabled="readonly" aria-label="任领导期间主要从事的业务线" /></td></tr>
          <tr><th>近三年获得奖励情况</th><td colspan="2" class="content-cell"><a-textarea v-model:value="payload.rewards_last_3y" :auto-size="{ minRows: 2, maxRows: 8 }" :disabled="readonly" aria-label="近三年奖励" /></td><th>近三年受到处理情况</th><td colspan="2" class="content-cell"><a-textarea v-model:value="payload.punishments_last_3y" :auto-size="{ minRows: 2, maxRows: 8 }" :disabled="readonly" aria-label="近三年处理" /></td></tr>
        </tbody>
      </table>
      <table class="sheet-grid" style="min-width:1000px;border-top:0">
        <colgroup><col style="width:42px" /><col style="width:100px" /><col style="width:260px" /><col /><col /><col v-for="grade in grades" :key="grade" style="width:36px" /></colgroup>
        <tbody>
          <tr><th :rowspan="payload.dimensions.length + 2" class="section-label vertical-label">自评情况</th><th rowspan="2" scope="col">内容</th><th rowspan="2" scope="col">自评要点</th><th rowspan="2" scope="col">现实表现</th><th rowspan="2" scope="col">存在不足</th><th :colspan="grades.length" scope="colgroup">自评</th></tr>
          <tr><th v-for="grade in grades" :key="grade" scope="col">{{ grade }}</th></tr>
          <tr v-for="row in payload.dimensions" :key="row.key"><th scope="row">{{ row.label }}</th><td class="point-copy">{{ row.content }}</td><td class="content-cell"><a-textarea v-model:value="row.performance" :auto-size="{ minRows: 3, maxRows: 12 }" :disabled="readonly" :aria-label="row.label + ' 现实表现'" /></td><td class="content-cell"><a-textarea v-model:value="row.shortcomings" :auto-size="{ minRows: 3, maxRows: 12 }" :disabled="readonly" :aria-label="row.label + ' 存在不足'" /></td><td v-for="grade in grades" :key="grade" class="choice-cell"><label class="choice-label"><input v-model="row.grade" class="sheet-radio" type="radio" :name="groupId + '-' + row.key" :value="grade" :disabled="readonly" :aria-label="row.label + ' ' + grade" /></label></td></tr>
        </tbody>
      </table>
      <table class="sheet-grid sheet-footer-grid" style="min-width:1000px"><tbody><tr><th scope="row">整改措施</th><td class="content-cell"><a-textarea v-model:value="payload.rectification" :auto-size="{ minRows: 3, maxRows: 12 }" :disabled="readonly" aria-label="整改措施" /></td></tr><tr><th scope="row">个人诉求</th><td class="content-cell"><a-textarea v-model:value="payload.personal_requests" :auto-size="{ minRows: 2, maxRows: 10 }" :disabled="readonly" aria-label="个人诉求" /></td></tr></tbody></table>
    </div>
  </div>
</template>
<script setup>
import { computed, useId } from 'vue'
const props = defineProps({ payload: { type: Object, required: true }, schema: { type: Object, default: () => ({}) }, readonly: Boolean })
const groupId = useId()
const grades = computed(() => props.schema.self_eval_grades || ['优', '良', '中', '差'])
</script>
