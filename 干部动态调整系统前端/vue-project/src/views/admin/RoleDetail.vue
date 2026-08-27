<template>
  <div class="page-shell">
    <a-card :title="role ? `配置角色：${role.name}` : '配置角色'" :loading="loading" :bordered="false">
      <a-alert v-if="role" type="info" show-icon :message="`${role.code} · 已分配 ${role.user_count} 名用户`" style="margin-bottom: 16px" />
      <a-checkbox-group v-model:value="selected">
        <a-card v-for="group in catalog" :key="group.module" size="small" :title="group.module" style="margin-bottom: 12px">
          <a-row><a-col v-for="item in group.permissions" :key="item.code" :span="12"><a-checkbox :value="item.code">{{ item.name }} <span class="code">{{ item.code }}</span></a-checkbox></a-col></a-row>
        </a-card>
      </a-checkbox-group>
      <a-space><a-button type="primary" :loading="saving" @click="save">保存权限</a-button><a-button @click="router.push('/admin/roles')">返回</a-button></a-space>
    </a-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import { getPermissionCatalog, getRole, updateRolePermissions } from '@/api/admin'
const route = useRoute(); const router = useRouter(); const role = ref(); const catalog = ref([]); const selected = ref([]); const loading = ref(true); const saving = ref(false)
const load = async () => { try { const [roleData, catalogData] = await Promise.all([getRole(route.params.id), getPermissionCatalog()]); role.value = roleData; selected.value = roleData.permissions || []; catalog.value = catalogData.catalog || [] } catch { message.error('角色信息加载失败') } finally { loading.value = false } }
const save = async () => { try { saving.value = true; await updateRolePermissions(route.params.id, selected.value); message.success('权限配置已保存') } catch (error) { message.error(error.response?.data?.permissions?.[0] || '保存失败') } finally { saving.value = false } }
onMounted(load)
</script>

<style scoped>.page-shell { min-height: calc(100vh - 48px); padding: 24px; background: #f5f7fa; } .code { color: #8c8c8c; font-size: 12px; }</style>
