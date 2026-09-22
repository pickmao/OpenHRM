<template>
  <div class="page-shell">
    <a-page-header :title="task?.form_label || '知事识人填报'" :sub-title="subTitle" @back="() => router.push({ name: 'KnowingPeopleTasks' })" />
    <a-spin :spinning="loading">
      <a-alert v-if="task?.return_reason" type="warning" show-icon :message="'管理员退回：' + task.return_reason" class="notice" />
      <a-alert v-if="task" type="info" show-icon :message="task.prefill_hint || '带花名册标记的字段来自人员库，可核对后修改。'" class="notice" />
      <a-card v-if="task" :title="task.form_label" :bordered="false">
        <component :is="formComponent" v-if="payload" :payload="payload" :schema="task.schema || {}" :readonly="readonly" :form-type="task.form_type" />
        <div class="actions">
          <a-space>
            <a-button v-if="!readonly" :loading="saving" @click="saveDraft">保存草稿</a-button>
            <a-button v-if="!readonly" type="primary" :loading="submitting" @click="submit">提交</a-button>
            <a-tag v-else color="green">{{ task.status_display }}</a-tag>
          </a-space>
        </div>
      </a-card>
    </a-spin>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import { knowingPeopleApi } from '@/api/knowingPeople'
import FormAttachment1 from './forms/FormAttachment1.vue'
import FormAttachment2 from './forms/FormAttachment2.vue'
import FormAttachment3 from './forms/FormAttachment3.vue'
import FormAttachment4 from './forms/FormAttachment4.vue'
import FormAttachment5 from './forms/FormAttachment5.vue'
import FormMatrix from './forms/FormMatrix.vue'

const route = useRoute()
const router = useRouter()
const task = ref(null)
const payload = ref(null)
const loading = ref(false)
const saving = ref(false)
const submitting = ref(false)

const readonly = computed(() => Boolean(task.value?.readonly || task.value?.status === 'SUBMITTED'))
const subTitle = computed(() => {
  if (!task.value) return ''
  const branch = task.value.branch_name || task.value.org_unit_name || '未关联组织'
  const deadline = task.value.deadline_at ? new Date(task.value.deadline_at).toLocaleString() : '—'
  return `${branch} · ${task.value.filler_role_label || ''} · 截止 ${deadline}`
})
const formComponent = computed(() => {
  const map = {
    ATTACHMENT_1: FormAttachment1,
    ATTACHMENT_2: FormAttachment2,
    ATTACHMENT_3: FormAttachment3,
    ATTACHMENT_4: FormAttachment4,
    ATTACHMENT_5: FormAttachment5,
    ATTACHMENT_6_1: FormMatrix,
    ATTACHMENT_6_2: FormMatrix,
    ATTACHMENT_7_1: FormMatrix,
    ATTACHMENT_7_2: FormMatrix,
    ATTACHMENT_7_3: FormMatrix,
    ATTACHMENT_7_4: FormMatrix
  }
  return map[task.value?.form_type] || FormAttachment2
})

const applyTask = data => {
  task.value = data
  payload.value = data.payload || {}
}

const firstError = value => {
  if (!value) return ''
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return firstError(value[0])
  if (typeof value === 'object') return firstError(value.detail || Object.values(value)[0])
  return String(value)
}

const load = async () => {
  loading.value = true
  try {
    applyTask(await knowingPeopleApi.getTask(route.params.id))
  } catch (error) {
    message.error(error.response?.data?.detail || '表单加载失败')
  } finally {
    loading.value = false
  }
}

const saveDraft = async () => {
  saving.value = true
  try {
    applyTask(await knowingPeopleApi.saveDraft(route.params.id, payload.value))
    message.success('草稿已保存')
  } catch (error) {
    message.error(firstError(error.response?.data) || '保存失败')
  } finally {
    saving.value = false
  }
}

const submit = async () => {
  submitting.value = true
  try {
    applyTask(await knowingPeopleApi.submitTask(route.params.id, payload.value))
    message.success('已提交')
  } catch (error) {
    message.error(firstError(error.response?.data) || '提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-shell { padding: 8px 16px 24px; }
.notice { margin-bottom: 16px; }
.actions { margin-top: 16px; }
</style>
