<template>
  <div class="page-shell"><a-card title="权限目录" :loading="loading" :bordered="false"><a-list :data-source="catalog" item-layout="vertical"><template #renderItem="{ item }"><a-list-item><a-list-item-meta :title="item.module" /><a-space wrap><a-tag v-for="permission in item.permissions" :key="permission.code">{{ permission.name }} · {{ permission.code }}</a-tag></a-space></a-list-item></template></a-list></a-card></div>
</template>
<script setup>
import { onMounted, ref } from 'vue'; import { message } from 'ant-design-vue'; import { getPermissionCatalog } from '@/api/admin'
const catalog = ref([]); const loading = ref(false); onMounted(async () => { loading.value = true; try { catalog.value = (await getPermissionCatalog()).catalog || [] } catch { message.error('权限目录加载失败') } finally { loading.value = false } })
</script>
<style scoped>.page-shell { min-height: calc(100vh - 48px); padding: 24px; background: #f5f7fa; }</style>
