<template>
  <div class="page-shell"><a-page-header title="领导班子研判分析" sub-title="基于当前有效版本的汇总统计" /><a-row :gutter="16" v-if="statistics"><a-col :span="6"><a-card><a-statistic title="文件版本" :value="statistics.total_files" /></a-card></a-col><a-col :span="6"><a-card><a-statistic title="有效版本" :value="statistics.active_files" /></a-card></a-col><a-col :span="6"><a-card><a-statistic title="班子记录" :value="statistics.total_records" /></a-card></a-col><a-col :span="6"><a-card><a-statistic title="平均得分" :value="statistics.average_score" :precision="2" /></a-card></a-col></a-row><a-card class="tips" title="指标说明">统计结果读取当前标记为“有效”的历史版本；可在“领导班子研判”页面切换版本并查看单条记录。</a-card></div>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import { leadershipAssessmentApi } from '@/api/assessments'
const statistics = ref(null)
onMounted(async () => { statistics.value = await leadershipAssessmentApi.getStatistics() })
</script>
<style scoped>.page-shell { padding: 8px 0; }.tips { margin-top: 16px; }</style>
