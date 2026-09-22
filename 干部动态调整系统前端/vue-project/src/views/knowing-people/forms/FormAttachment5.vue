<template>
  <div>
    <a-alert type="info" show-icon message="结合本次考察年度的急难险重任务、复杂问题和重大考验等重点工作述事；按主导者、协助者、执行者记录具体人员及作用，角色可多选。" style="margin-bottom:16px" />
    <a-row :gutter="16">
      <a-col :span="12"><a-form-item label="党支部名称" required><a-input v-model:value="payload.branch_name" :disabled="readonly" /><a-tag v-if="prefill('branch_name')" color="blue">组织树</a-tag></a-form-item></a-col>
      <a-col :span="12"><a-form-item label="填报时间"><a-date-picker v-model:value="payload.fill_date" value-format="YYYY-MM-DD" style="width:100%" :disabled="readonly" /></a-form-item></a-col>
    </a-row>
    <div v-for="(work, wIndex) in payload.works" :key="wIndex" class="work-block">
      <div class="work-title">
        重点工作 {{ wIndex + 1 }}
        <a-button v-if="!readonly" type="link" danger @click="removeWork(wIndex)">删除该工作</a-button>
      </div>
      <a-form-item label="重点工作名称"><a-input v-model:value="work.title" :disabled="readonly" /></a-form-item>
      <a-form-item label="简要表述"><a-textarea v-model:value="work.description" :rows="3" :disabled="readonly" /></a-form-item>
      <div v-for="(person, pIndex) in work.people" :key="pIndex" class="person-block">
        <a-row :gutter="12">
          <a-col :span="8"><a-form-item label="具体人员"><a-auto-complete v-model:value="person.name" :options="peopleOptions" :filter-option="filterPerson" :disabled="readonly" placeholder="选择本支部人员或输入姓名" style="width:100%" /></a-form-item></a-col>
          <a-col :span="12">
            <a-form-item label="承担角色">
              <a-checkbox-group v-model:value="person.roles" :disabled="readonly" :options="schema.roles || ['主导者', '协助者', '执行者']" />
            </a-form-item>
          </a-col>
          <a-col :span="4" class="person-action">
            <a-button v-if="!readonly" type="link" danger @click="removePerson(work, pIndex)">删除人员</a-button>
          </a-col>
          <a-col :span="24"><a-form-item label="具体任务和作用发挥"><a-textarea v-model:value="person.task_and_role" :rows="3" :disabled="readonly" /></a-form-item></a-col>
        </a-row>
      </div>
      <a-button v-if="!readonly" size="small" @click="addPerson(work)">在该工作下增加人员</a-button>
    </div>
    <a-button v-if="!readonly" type="dashed" block @click="addWork">新增重点工作</a-button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ payload: { type: Object, required: true }, schema: { type: Object, default: () => ({}) }, readonly: Boolean })
const peopleOptions = computed(() => (props.schema.roster_people || []).map(person => ({ value: person.name, label: `${person.name}（${person.department}）` })))
const filterPerson = (input, option) => option.label.includes(input)
const prefill = key => (props.payload.prefill_fields || []).includes(key)
const addWork = () => {
  props.payload.works = [...(props.payload.works || []), { title: '', description: '', people: [{ name: '', roles: [], task_and_role: '' }] }]
}
const removeWork = index => props.payload.works.splice(index, 1)
const addPerson = work => { work.people = [...(work.people || []), { name: '', roles: [], task_and_role: '' }] }
const removePerson = (work, index) => work.people.splice(index, 1)
</script>

<style scoped>
.work-block { border: 1px solid #f0f0f0; padding: 12px 16px; margin-bottom: 16px; border-radius: 8px; }
.work-title { font-weight: 600; margin-bottom: 8px; }
.person-block { background: #fafafa; padding: 8px 12px; margin-bottom: 8px; border-radius: 6px; }
.person-action { display: flex; align-items: center; }
</style>
