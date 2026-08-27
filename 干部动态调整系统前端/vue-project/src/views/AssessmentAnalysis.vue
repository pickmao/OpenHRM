<template>
  <div class="page-shell">
    <a-page-header title="中层干部研判分析" sub-title="基于当前有效版本的汇总统计" />
    <a-row :gutter="16" v-if="statistics"><a-col :span="8"><a-card><a-statistic title="文件版本" :value="statistics.total_files" /></a-card></a-col><a-col :span="8"><a-card><a-statistic title="有效版本" :value="statistics.active_files" /></a-card></a-col><a-col :span="8"><a-card><a-statistic title="研判记录" :value="statistics.total_records" /></a-card></a-col></a-row>
    <a-card title="职务类别分布" class="distribution"><a-table :columns="columns" :data-source="categories" :pagination="false" row-key="name" /></a-card>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { assessmentApi } from '@/api/assessments'
const statistics = ref(null)
const categories = computed(() => Object.entries(statistics.value?.category_stats || {}).map(([name, count]) => ({ name, count })))
const columns = [{ title: '职务类别', dataIndex: 'name' }, { title: '人数', dataIndex: 'count', width: 180 }]
onMounted(async () => { statistics.value = await assessmentApi.getStatistics() })
</script>
<style scoped>.page-shell { padding: 8px 0; }.distribution { margin-top: 16px; }</style>
