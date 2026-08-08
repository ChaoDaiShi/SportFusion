<template>
  <div class="data-table-wrap">
    <el-table
      :data="data"
      v-bind="$attrs"
      stripe
      border
      height="400"
      style="width: 100%"
      @selection-change="onSelect"
    >
      <el-table-column v-if="selectable" type="selection" width="50" />
      <el-table-column
        v-for="col in columns"
        :key="col.prop"
        :prop="col.prop"
        :label="col.label"
        :width="col.width"
        :min-width="col.minWidth"
        :formatter="col.formatter"
        show-overflow-tooltip
      />
    </el-table>
    <div class="pagination-wrap" v-if="showPagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="$emit('page-change', $event)"
        @size-change="$emit('size-change', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  columns: { type: Array, default: () => [] },
  selectable: { type: Boolean, default: false },
  total: { type: Number, default: 0 },
  showPagination: { type: Boolean, default: false },
})

defineEmits(['page-change', 'size-change', 'select-change'])

const currentPage = ref(1)
const pageSize = ref(20)

function onSelect(rows) {
  // emit('select-change', rows)
}
</script>

<style scoped>
.data-table-wrap { background: #fff; border-radius: 4px; padding: 16px; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
