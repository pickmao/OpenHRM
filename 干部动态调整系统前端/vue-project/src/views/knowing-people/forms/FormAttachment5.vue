<template>
  <div>
    <div class="sheet-attachment">附件5</div><h2 class="sheet-title">近距离考察干部支部述事表</h2>
    <div class="sheet-meta"><label><span>党支部名称（盖章）：</span><a-input v-model:value="payload.branch_name" :disabled="readonly" aria-label="党支部名称" /></label><label><span>填报时间：</span><a-date-picker v-model:value="payload.fill_date" value-format="YYYY-MM-DD" :disabled="readonly" aria-label="填报时间" /></label></div>
    <div class="sheet-scroll">
      <table class="sheet-grid" style="min-width:1100px">
        <colgroup><col style="width:42px" /><col style="width:58px" /><col style="width:170px" /><col style="width:220px" /><col style="width:126px" /><col style="width:184px" /><col /></colgroup>
        <tbody>
          <tr><th :rowspan="totalRows + 1" class="section-label vertical-label">述事记录</th><th scope="col">序号</th><th scope="col">重点工作</th><th scope="col">简要表述</th><th scope="col">承担角色</th><th scope="col">具体人员</th><th scope="col">具体任务和作用发挥</th></tr>
          <template v-for="(work, wIndex) in payload.works" :key="wIndex">
            <tr v-for="(person, pIndex) in visiblePeople(work)" :key="pIndex" :data-work-index="wIndex" :data-person-index="pIndex">
              <td v-if="pIndex === 0" :rowspan="workRows(work)">{{ wIndex + 1 }}<div v-if="!readonly" class="cell-actions"><a-button type="text" danger size="small" :aria-label="'删除第' + (wIndex + 1) + '项工作'" @click="removeWork(wIndex)">删除</a-button></div></td>
              <td v-if="pIndex === 0" :rowspan="workRows(work)" class="content-cell"><label class="cell-label">材料年度<a-date-picker v-model:value="work.year" picker="year" value-format="YYYY" :disabled="readonly" :aria-label="'第' + (wIndex + 1) + '项工作材料年度'" placeholder="选择年度" /></label><a-textarea v-model:value="work.title" :auto-size="{ minRows: 3, maxRows: 8 }" :disabled="readonly" :aria-label="'第' + (wIndex + 1) + '项重点工作名称'" placeholder="填写重点工作名称" /></td>
              <td v-if="pIndex === 0" :rowspan="workRows(work)" class="content-cell"><a-textarea v-model:value="work.description" :auto-size="{ minRows: 4, maxRows: 14 }" :disabled="readonly" :aria-label="'第' + (wIndex + 1) + '项工作简要表述'" /></td>
              <template v-if="person">
                <td class="roles-column"><a-checkbox-group v-model:value="person.roles" :disabled="readonly" :options="schema.roles || ['主导者', '协助者', '执行者']" /></td>
                <td class="content-cell"><a-select v-if="!readonly || person.roster_id" :value="person.roster_id || undefined" :options="peopleOptions" show-search option-filter-prop="label" allow-clear :disabled="readonly" :aria-label="'第' + (wIndex + 1) + '项工作第' + (pIndex + 1) + '名具体人员'" placeholder="选择花名册人员" @change="value => selectPerson(person, value)" /><a-input v-if="!person.roster_id" v-model:value="person.name" :disabled="readonly" placeholder="或填写姓名，待核对身份" :aria-label="'第' + (wIndex + 1) + '项工作第' + (pIndex + 1) + '名人员姓名'" /><div v-if="!readonly" class="cell-actions"><a-button type="text" danger size="small" :aria-label="'删除第' + (wIndex + 1) + '项工作第' + (pIndex + 1) + '名人员'" @click="removePerson(work, pIndex)">删除人员</a-button></div></td>
                <td class="content-cell"><a-textarea v-model:value="person.task_and_role" :auto-size="{ minRows: 4, maxRows: 12 }" :disabled="readonly" :aria-label="'第' + (wIndex + 1) + '项工作第' + (pIndex + 1) + '名人员具体任务和作用发挥'" /></td>
              </template>
              <td v-else colspan="3" class="sheet-empty">本项工作尚未填写具体人员。</td>
            </tr>
            <tr v-if="!readonly"><td colspan="3" class="sheet-row-actions"><a-button size="small" :aria-label="'第' + (wIndex + 1) + '项工作增加人员'" @click="addPerson(work)">增加人员</a-button></td></tr>
          </template>
          <tr v-if="!(payload.works || []).length"><td colspan="7" class="sheet-empty">暂无述事记录，请新增重点工作。</td></tr>
        </tbody>
      </table>
    </div>
    <a-button v-if="!readonly" class="sheet-add" type="dashed" @click="addWork">新增重点工作</a-button>
    <p class="sheet-note">按实际材料年度填写重点工作。同一项工作可填写多名人员，承担角色可多选；所填工作与人员作用将归集到对应年度的研判表。</p>
  </div>
</template>
<script setup>
import { computed } from 'vue'
const props = defineProps({ payload: { type: Object, required: true }, schema: { type: Object, default: () => ({}) }, readonly: Boolean })
const peopleOptions = computed(() => (props.schema.roster_people || []).map(person => ({ value: person.id, label: person.name + '（' + person.department + ' · ' + (person.position || '职务未填') + '）' })))
const selectPerson = (person, value) => { const selected = (props.schema.roster_people || []).find(item => item.id === value); Object.assign(person, { roster_id: selected?.id || '', name: selected?.name || person.name || '', department: selected?.department || '' }) }
const visiblePeople = work => work.people?.length ? work.people : [null]
const workRows = work => visiblePeople(work).length + (props.readonly ? 0 : 1)
const totalRows = computed(() => (props.payload.works || []).reduce((count, work) => count + workRows(work), 0))
const addWork = () => { props.payload.works = [...(props.payload.works || []), { year: props.schema.campaign_year || '', title: '', description: '', people: [{ name: '', roles: [], task_and_role: '' }] }] }
const removeWork = index => props.payload.works.splice(index, 1)
const addPerson = work => { work.people = [...(work.people || []), { name: '', roles: [], task_and_role: '' }] }
const removePerson = (work, index) => work.people.splice(index, 1)
</script>
