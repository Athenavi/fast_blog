<script generic="T" lang="ts" setup>
/**
 * 后台列表壳：把列表页的"公共骨架"一次写好，页面只提供列定义与少量插槽。
 *
 * 提供：筛选栏（`#filters`）· 工具条（`#actions`）· 批量操作条（`#bulk`）·
 * 空状态（`#empty-actions`）· 首次加载骨架屏 · 分页 · 选择与分页事件透传。
 *
 * 用法：
 *   <AdminListShell
 *     :loading="list.loading.value" :rows="list.rows.value" :total="list.total.value"
 *     :page="list.page.value" :page-size="list.pageSize.value"
 *     :selection-count="list.selectedCount.value"
 *     :empty-title="$t('admin.content.article.emptyTitle')"
 *     @search="list.search" @reset="list.reset" @refresh="list.reload"
 *     @page-change="list.onPageChange" @size-change="list.onSizeChange"
 *     @selection-change="list.onSelectionChange" @clear-selection="list.clearSelection"
 *   >
 *     <template #filters>…查询项…</template>
 *     <template #actions>…主操作按钮…</template>
 *     <template #bulk>…批量按钮…</template>
 *     <el-table-column …/>   <!-- 列定义放默认插槽 -->
 *   </AdminListShell>
 */
import {Refresh, Search} from '@element-plus/icons-vue'

withDefaults(
  defineProps<{
    rows: T[]
    total: number
    page: number
    pageSize: number
    loading?: boolean
    /** 最近一次加载失败（展示错误态而不是"暂无数据"） */
    failed?: boolean
    selectable?: boolean
    /** 接口不分页时置 false：不渲染分页器（工具条的"共 N 条"仍保留） */
    paginate?: boolean
    rowKey?: string
    emptyTitle?: string
    emptyDesc?: string
    selectionCount?: number
    pageSizes?: number[]
  }>(),
  {
    loading: false,
    failed: false,
    selectable: true,
    paginate: true,
    rowKey: 'id',
    selectionCount: 0,
    pageSizes: () => [10, 20, 50, 100],
  },
)

defineEmits<{
  (event: 'search'): void
  (event: 'reset'): void
  (event: 'refresh'): void
  (event: 'page-change', page: number): void
  (event: 'size-change', size: number): void
  (event: 'selection-change', rows: T[]): void
  (event: 'clear-selection'): void
}>()

const {t} = useI18n()
</script>

<template>
  <div class="admin-card admin-list">
    <div v-if="$slots.filters" class="admin-list__filters">
      <el-form :inline="true" class="admin-filter" @submit.prevent="$emit('search')">
        <slot name="filters"/>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="$emit('search')">
            {{ $t('admin.common.search') }}
          </el-button>
          <el-button :icon="Refresh" @click="$emit('reset')">{{ $t('admin.common.reset') }}</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="admin-toolbar">
      <slot name="actions"/>
      <span class="admin-toolbar__spacer"/>
      <span class="admin-toolbar__total">{{ t('admin.common.totalItems', {n: total}) }}</span>
      <el-button :icon="Refresh" :title="$t('admin.common.refresh')" circle @click="$emit('refresh')"/>
    </div>

    <AdminSelectionBar
      v-if="selectable"
      :count="selectionCount"
      @clear="$emit('clear-selection')"
    >
      <slot name="bulk"/>
    </AdminSelectionBar>

    <AdminTableSkeleton v-if="loading && !rows.length" :rows="6"/>

    <AdminEmpty
      v-else-if="!loading && !rows.length"
      :desc="emptyDesc"
      :title="emptyTitle ?? (failed ? t('admin.common.loadFailed') : t('admin.common.empty'))"
      :variant="failed ? 'error' : 'default'"
    >
      <el-button v-if="failed" :icon="Refresh" @click="$emit('refresh')">
        {{ $t('admin.common.retry') }}
      </el-button>
      <slot v-else name="empty-actions"/>
    </AdminEmpty>

    <template v-else>
      <el-table
        v-loading="loading"
        :data="rows"
        :row-key="rowKey"
        border
        stripe
        @selection-change="$emit('selection-change', $event as T[])"
      >
        <el-table-column v-if="selectable" :reserve-selection="false" type="selection" width="46"/>
        <slot/>
      </el-table>

      <el-pagination
        v-if="paginate && total > 0"
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="pageSizes"
        :total="total"
        background
        class="admin-pagination"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="$emit('page-change', $event)"
        @size-change="$emit('size-change', $event)"
      />
    </template>
  </div>
</template>

<style scoped>
.admin-list {
  padding: var(--admin-gap-lg);
}

.admin-list__filters {
  padding-bottom: var(--admin-gap-xs);
}
</style>
