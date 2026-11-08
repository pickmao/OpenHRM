<template>
  <div class="matrix-tools"><a-button type="text" size="small" @click="showDescriptions = !showDescriptions">{{ showDescriptions ? '收起评价要点' : '展开评价要点' }}</a-button></div>
  <div class="sheet-scroll score-scroll" :style="{ scrollPaddingTop: (headerHeight + 6) + 'px', scrollPaddingLeft: (42 + nameWidth) + 'px', scrollPaddingBottom: '12px' }" tabindex="0" aria-label="测评表，可横向滚动查看全部评价列">
    <table class="sheet-grid score-matrix" :style="{ minWidth: `${minWidth}px` }">
      <colgroup><col style="width:42px" /><col :style="{ width: `${nameWidth}px` }" /><col v-if="showPosition" style="width:120px" /><template v-for="dim in dimensions" :key="dim.key"><col v-for="grade in grades" :key="grade" style="width:30px" /></template><template v-if="showRecognition"><col v-for="option in recognitionOptions" :key="option" style="width:34px" /></template></colgroup>
      <thead ref="tableHead">
        <tr><th :rowspan="showDescriptions ? 3 : 2" scope="col" class="matrix-index">序号</th><th :rowspan="showDescriptions ? 3 : 2" scope="col" class="matrix-name group-end">{{ identityLabel }}</th><th v-if="showPosition" :rowspan="showDescriptions ? 3 : 2" scope="col" class="group-end">职务／职级</th><th v-for="dim in dimensions" :key="dim.key" :colspan="grades.length" scope="colgroup" class="dimension-title group-end">{{ dim.label }}</th><th v-if="showRecognition" :colspan="recognitionOptions.length" :rowspan="showDescriptions ? 2 : 1" scope="colgroup">工作认可度</th></tr>
        <tr v-if="showDescriptions"><th v-for="dim in dimensions" :key="dim.key" :colspan="grades.length" class="dimension-description group-end">{{ dim.content }}</th></tr>
        <tr><template v-for="dim in dimensions" :key="dim.key"><th v-for="(grade, index) in grades" :key="grade" scope="col" class="grade-heading" :class="{ 'group-end': index === grades.length - 1 }">{{ grade }}</th></template><template v-if="showRecognition"><th v-for="option in recognitionOptions" :key="option" scope="col" class="grade-heading">{{ option }}</th></template></tr>
      </thead>
      <tbody>
        <tr v-for="(target, index) in rows" :key="target.id || index"><td class="matrix-index">{{ index + 1 }}</td><th scope="row" class="matrix-name group-end">{{ target.name }}<div v-if="showPosition && target.department" class="cell-note">{{ target.department }}</div></th><td v-if="showPosition" class="group-end">{{ target.position || '—' }}</td><template v-for="dim in dimensions" :key="dim.key"><td v-for="(grade, gradeIndex) in grades" :key="grade" class="choice-cell" :class="{ 'group-end': gradeIndex === grades.length - 1 }"><label class="choice-label"><input v-model="target.scores[dim.key]" class="sheet-radio" type="radio" :name="`${groupId}-${target.id || index}-${dim.key}`" :value="grade" :disabled="readonly" :aria-label="`${target.name} ${dim.label} ${grade}`" /></label></td></template><template v-if="showRecognition"><td v-for="option in recognitionOptions" :key="option" class="choice-cell"><label class="choice-label"><input v-model="(recognitionOwner || target).recognition" class="sheet-radio" type="radio" :name="`${groupId}-${target.id || index}-recognition`" :value="option" :disabled="readonly" :aria-label="`${target.name} 工作认可度 ${option}`" /></label></td></template></tr>
        <tr v-if="!rows.length"><td :colspan="identityColumns + scoreColumns" class="sheet-empty">暂无评价对象，请联系管理员核对下发名单。</td></tr>
      </tbody>
      <tfoot v-if="$slots.footer"><slot name="footer" :identity-columns="identityColumns" :score-columns="scoreColumns" /></tfoot>
    </table>
  </div>
</template>
<script setup>
import { computed, onBeforeUnmount, onMounted, ref, useId } from 'vue'
const props = defineProps({ rows: { type: Array, default: () => [] }, dimensions: { type: Array, default: () => [] }, grades: { type: Array, default: () => ['优', '良', '中', '差'] }, identityLabel: { type: String, default: '姓名' }, showPosition: Boolean, showRecognition: Boolean, recognitionOptions: { type: Array, default: () => ['认可', '基本认可', '不认可', '不了解'] }, recognitionOwner: { type: Object, default: null }, readonly: Boolean })
const groupId = useId()
const showDescriptions = ref(true)
const tableHead = ref(null)
const headerHeight = ref(0)
let headerObserver
onMounted(() => {
  const updateHeader = () => { headerHeight.value = tableHead.value?.getBoundingClientRect().height || 0 }
  updateHeader()
  headerObserver = new ResizeObserver(updateHeader)
  headerObserver.observe(tableHead.value)
})
onBeforeUnmount(() => headerObserver?.disconnect())
const identityColumns = computed(() => props.showPosition ? 3 : 2)
const scoreColumns = computed(() => props.dimensions.length * props.grades.length + (props.showRecognition ? props.recognitionOptions.length : 0))
const nameWidth = computed(() => props.showPosition ? 100 : 160)
const minWidth = computed(() => 42 + nameWidth.value + (props.showPosition ? 120 : 0) + props.dimensions.length * props.grades.length * 30 + (props.showRecognition ? props.recognitionOptions.length * 34 : 0))
</script>
