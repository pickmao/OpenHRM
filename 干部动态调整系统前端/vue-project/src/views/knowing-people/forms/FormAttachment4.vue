<template>
  <div>
    <div class="sheet-attachment">附件4</div><h2 class="sheet-title">近距离考察干部评价表</h2>
    <div class="sheet-meta"><label><span>党支部（盖章）：</span><a-input v-model:value="payload.branch_name" :disabled="readonly" aria-label="党支部名称" /></label><label><span>评价时间：</span><a-date-picker v-model:value="payload.eval_date" value-format="YYYY-MM-DD" :disabled="readonly" aria-label="评价时间" /></label></div>
    <div class="sheet-scroll">
      <table class="sheet-grid" style="min-width:1080px">
        <colgroup><col style="width:42px" /><col style="width:110px" /><col v-for="n in 8" :key="n" /></colgroup>
        <tbody>
          <tr><th rowspan="2" class="section-label vertical-label">班子基本情况</th><th>人员配备</th><template v-for="field in staffingFields" :key="field.key"><th>{{ field.label }}</th><td><a-input-number v-model:value="payload[field.key]" :min="0" :precision="0" :disabled="readonly" :aria-label="field.label" /></td></template></tr>
          <tr><th>班子阅历结构（人）</th><th>长期在机关</th><td colspan="2"><a-input-number v-model:value="payload.experience_counts.office" :min="0" :precision="0" :disabled="readonly" aria-label="长期在机关人数" /></td><th>相对均衡</th><td colspan="2"><a-input-number v-model:value="payload.experience_counts.balanced" :min="0" :precision="0" :disabled="readonly" aria-label="经历相对均衡人数" /></td><th>长期在监区</th><td><a-input-number v-model:value="payload.experience_counts.prison" :min="0" :precision="0" :disabled="readonly" aria-label="长期在监区人数" /></td></tr>
        </tbody>
      </table>
      <table class="sheet-grid" style="min-width:1080px;border-top:0">
        <colgroup><col style="width:42px" /><col style="width:80px" /><col style="width:100px" /><col style="width:240px" /><col /><col /><col v-for="grade in grades" :key="grade" style="width:38px" /></colgroup>
        <tbody>
          <tr><th :rowspan="payload.items.length + 2" class="section-label vertical-label">评价情况</th><th rowspan="2" scope="col">内容</th><th colspan="2" rowspan="2" scope="col">评价要点</th><th rowspan="2" scope="col">现实表现</th><th rowspan="2" scope="col">存在不足</th><th :colspan="grades.length" scope="colgroup">评价</th></tr>
          <tr><th v-for="grade in grades" :key="grade" scope="col">{{ grade }}</th></tr>
          <tr v-for="(row, index) in payload.items" :key="row.key">
            <th v-if="categorySpan(index)" :rowspan="categorySpan(index)" scope="rowgroup" class="category-cell">{{ row.category }}</th><th scope="row">{{ row.label }}</th><td class="point-copy">{{ row.content }}</td>
            <td class="content-cell"><a-textarea v-model:value="row.performance" :auto-size="{ minRows: 3, maxRows: 12 }" :disabled="readonly" :aria-label="row.label + ' 现实表现'" /></td>
            <td class="content-cell"><a-textarea v-model:value="row.shortcomings" :auto-size="{ minRows: 3, maxRows: 12 }" :disabled="readonly" :aria-label="row.label + ' 存在不足'" /></td>
            <td v-for="grade in grades" :key="grade" class="choice-cell"><label class="choice-label"><input v-model="row.grade" type="radio" class="sheet-radio" :name="groupId + '-' + row.key" :value="grade" :disabled="readonly" :aria-label="row.label + ' ' + grade" /></label></td>
          </tr>
        </tbody>
      </table>
      <table class="sheet-grid sheet-footer-grid" style="min-width:1080px"><tbody>
        <tr><th scope="row">整改措施</th><td colspan="3" class="content-cell"><a-textarea v-model:value="payload.rectification" :auto-size="{ minRows: 3, maxRows: 12 }" :disabled="readonly" aria-label="整改措施" /></td></tr>
        <tr><th scope="row">班子诉求</th><td colspan="3" class="content-cell"><a-textarea v-model:value="payload.team_requests" :auto-size="{ minRows: 2, maxRows: 10 }" :disabled="readonly" aria-label="班子诉求" /></td></tr>
        <tr><th scope="row">是否需要调整</th><td><a-radio-group v-model:value="payload.adjustment_needed" :disabled="readonly"><a-radio value="是">是</a-radio><a-radio value="否">否</a-radio></a-radio-group></td><th scope="row">调整建议</th><td class="content-cell"><a-textarea v-model:value="payload.adjustment_suggestion" :auto-size="{ minRows: 2, maxRows: 10 }" :disabled="readonly" aria-label="调整建议" /></td></tr>
      </tbody></table>
    </div>
    <p class="sheet-note">人员配备和阅历结构按人数填写，没有则填0；每个评价项目选择一个档次。<span v-if="payload.experience_structure">历史阅历记录：{{ payload.experience_structure }}，请核对后补充人数。</span></p>
  </div>
</template>
<script setup>
import { computed, useId } from 'vue'
const props = defineProps({ payload: { type: Object, required: true }, schema: { type: Object, default: () => ({}) }, readonly: Boolean })
const groupId = useId()
if (!props.payload.experience_counts) props.payload.experience_counts = { office: null, balanced: null, prison: null }
const grades = computed(() => props.schema.self_eval_grades || ['优', '良', '中', '差'])
const staffingFields = [{ key: 'leadership_current', label: '监区（部门）领导现有人数' }, { key: 'leadership_vacancy', label: '监区（部门）领导空缺人数' }, { key: 'team_leader_current', label: '工作团队负责人现有人数' }, { key: 'team_leader_vacancy', label: '工作团队负责人空缺人数' }]
const categorySpan = index => {
  const items = props.payload.items || []
  if (index && items[index - 1].category === items[index].category) return 0
  let count = 1
  while (items[index + count]?.category === items[index].category) count++
  return count
}
</script>
