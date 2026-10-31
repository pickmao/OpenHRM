<template>
  <div class="allocation-page">
    <a-result
      status="info"
      title="当前为直接生效模式"
      sub-title="系统不提供调配审批。提交部门调配后人员归属立即变更。"
    >
      <template #extra>
        <a-button type="primary" @click="$router.replace('/allocation/plan')">前往部门调配</a-button>
      </template>
    </a-result>
  </div>
</template>

<script setup>
</script>

<style scoped>
.allocation-page {
  min-height: calc(100vh - 48px);
  padding: 24px;
  background: #f5f7fa;
}
</style>
