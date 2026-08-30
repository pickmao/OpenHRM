<template>
  <div class="page-shell">
    <a-card title="新建角色" :bordered="false">
      <a-form ref="formRef" :model="form" :rules="rules" :label-col="{ span: 4 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="角色编码" name="code"><a-input v-model:value="form.code" placeholder="例如 BUSINESS_ADMIN" /></a-form-item>
        <a-form-item label="角色名称" name="name"><a-input v-model:value="form.name" /></a-form-item>
        <a-form-item label="角色说明"><a-textarea v-model:value="form.description" /></a-form-item>
        <a-form-item label="启用"><a-switch v-model:checked="form.is_active" /></a-form-item>
        <a-form-item :wrapper-col="{ offset: 4 }"><a-space><a-button type="primary" :loading="saving" @click="save">保存</a-button><a-button @click="router.push('/admin/roles')">取消</a-button></a-space></a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { createRole } from '@/api/admin'
import { registerModelContextTools } from '@/utils/webmcp'
const router = useRouter(); const formRef = ref(); const saving = ref(false)
const form = reactive({ code: '', name: '', description: '', is_active: true, permissions: [] })
const rules = { code: [{ required: true, message: '请输入角色编码' }], name: [{ required: true, message: '请输入角色名称' }] }
const save = async () => { try { await formRef.value.validate(); saving.value = true; await createRole(form); message.success('角色已创建，请继续配置权限'); router.push('/admin/roles') } catch (error) { if (!error?.errorFields) message.error(error.response?.data?.code?.[0] || '创建失败') } finally { saving.value = false } }
let unregisterWebMcpTools = () => {}
const roleSchema = {
  type: 'object',
  properties: {
    code: { type: 'string', minLength: 1, description: '唯一角色编码，例如 BUSINESS_ADMIN' },
    name: { type: 'string', minLength: 1, description: '角色显示名称' },
    description: { type: 'string', description: '角色说明' },
    isActive: { type: 'boolean', description: '是否启用，默认 true' }
  }, required: ['code', 'name'], additionalProperties: false
}
const applyRoleDraft = async input => {
  form.code = input.code.trim(); form.name = input.name.trim(); form.description = input.description || ''; form.is_active = input.isActive ?? true
  await nextTick()
}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'stage_openhrm_role_creation', title: '配置新角色',
      description: '在新建角色页面填写角色信息，仅暂存于当前页面，不会创建角色。',
      inputSchema: roleSchema, annotations: { readOnlyHint: false },
      async execute(input) { await applyRoleDraft(input); return { status: 'staged', code: form.code, name: form.name, isActive: form.is_active } }
    },
    {
      name: 'complete_openhrm_role_creation', title: '创建角色',
      description: '创建一个新角色并返回角色列表；这是会写入系统的操作。',
      inputSchema: roleSchema, annotations: { readOnlyHint: false },
      async execute(input) {
        await applyRoleDraft(input)
        if (!form.code || !form.name) throw new Error('角色编码和角色名称不能为空')
        saving.value = true
        try {
          const created = await createRole({ ...form }); message.success('角色已创建'); await router.push('/admin/roles')
          return { status: 'created', role: { id: created.id, code: created.code, name: created.name } }
        } finally { saving.value = false }
      }
    }
  ])
}
onMounted(registerWebMcpTools)
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>.page-shell { min-height: calc(100vh - 48px); padding: 24px; background: #f5f7fa; }</style>
