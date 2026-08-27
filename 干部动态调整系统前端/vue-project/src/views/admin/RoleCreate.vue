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
import { reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { createRole } from '@/api/admin'
const router = useRouter(); const formRef = ref(); const saving = ref(false)
const form = reactive({ code: '', name: '', description: '', is_active: true, permissions: [] })
const rules = { code: [{ required: true, message: '请输入角色编码' }], name: [{ required: true, message: '请输入角色名称' }] }
const save = async () => { try { await formRef.value.validate(); saving.value = true; await createRole(form); message.success('角色已创建，请继续配置权限'); router.push('/admin/roles') } catch (error) { if (!error?.errorFields) message.error(error.response?.data?.code?.[0] || '创建失败') } finally { saving.value = false } }
</script>

<style scoped>.page-shell { min-height: calc(100vh - 48px); padding: 24px; background: #f5f7fa; }</style>
