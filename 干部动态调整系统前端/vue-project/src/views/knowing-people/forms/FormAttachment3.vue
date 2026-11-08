<template>
  <div>
    <div class="sheet-attachment">附件3</div><h2 class="sheet-title">近距离考察干部个人述事表</h2>
    <div class="sheet-scroll">
      <table class="sheet-grid" style="min-width:1000px">
        <colgroup><col style="width:42px" /><col style="width:100px" /><col /><col style="width:100px" /><col /><col style="width:100px" /><col /></colgroup>
        <tbody><tr><th rowspan="2" class="section-label vertical-label">基本情况</th><th>姓名</th><td><a-input v-model:value="payload.name" :disabled="readonly" aria-label="姓名" /></td><th>性别</th><td><a-input v-model:value="payload.gender" :disabled="readonly" aria-label="性别" /></td><th>出生年月</th><td><a-input v-model:value="payload.birth_date" :disabled="readonly" aria-label="出生年月" placeholder="YYYY-MM" /></td></tr><tr><th>现部门及职务</th><td><a-input v-model:value="payload.department_position" :disabled="readonly" aria-label="现部门及职务" /></td><th>任现职务时间</th><td><a-input v-model:value="payload.current_position_date" :disabled="readonly" aria-label="任现职务时间" /></td><th>政治面貌</th><td><a-input v-model:value="payload.political_status" :disabled="readonly" aria-label="政治面貌" /></td></tr></tbody>
      </table>
      <table class="sheet-grid" style="min-width:1000px;border-top:0">
        <colgroup><col style="width:42px" /><col style="width:190px" /><col style="width:190px" /><col style="width:132px" /><col /></colgroup>
        <tbody><tr><th :rowspan="payload.items.length + 1" class="section-label vertical-label">述事记录</th><th scope="col">任职经历</th><th scope="col">重点工作</th><th scope="col">承担角色</th><th scope="col">事情详细情况</th></tr>
          <tr v-for="(row, index) in payload.items" :key="index" :data-story-index="index"><td class="content-cell"><a-textarea v-model:value="row.experience" :auto-size="{ minRows: 4, maxRows: 12 }" :disabled="readonly" :aria-label="'第' + (index + 1) + '条任职经历'" /><a-button v-if="!readonly" type="text" danger size="small" :aria-label="'删除第' + (index + 1) + '条重点工作'" @click="remove(index)">删除本条</a-button></td><td class="content-cell"><a-textarea v-model:value="row.key_work" :auto-size="{ minRows: 4, maxRows: 12 }" :disabled="readonly" :aria-label="'第' + (index + 1) + '条重点工作'" /></td><td class="roles-column"><a-checkbox-group v-model:value="row.roles" :disabled="readonly" :options="schema.roles || ['主导者', '协助者', '执行者']" /></td><td class="content-cell"><a-textarea v-model:value="row.details" :auto-size="{ minRows: 5, maxRows: 16 }" :disabled="readonly" :aria-label="'第' + (index + 1) + '条事情详细情况'" /></td></tr>
          <tr v-if="!payload.items.length"><td colspan="5" class="sheet-empty">暂无述事记录，请新增重点工作。</td></tr>
        </tbody>
      </table>
    </div>
    <a-button v-if="!readonly" class="sheet-add" type="dashed" @click="add">新增一条重点工作</a-button>
    <p class="sheet-note">任职经历具体至年月，重点表述在急难险重任务、复杂问题和重大考验中承担的任务和作用；承担角色可多选。</p>
    <div class="sheet-meta" style="margin-top:20px"><label><span>个人签名：</span><a-input v-model:value="payload.signature" :disabled="readonly" aria-label="个人签名" /></label><label><span>填写时间：</span><a-date-picker v-model:value="payload.fill_date" value-format="YYYY-MM-DD" :disabled="readonly" aria-label="填写时间" /></label></div>
  </div>
</template>
<script setup>
const props = defineProps({ payload: { type: Object, required: true }, schema: { type: Object, default: () => ({}) }, readonly: Boolean })
const add = () => { props.payload.items = [...(props.payload.items || []), { experience: '', key_work: '', roles: [], details: '' }] }
const remove = index => props.payload.items.splice(index, 1)
</script>
