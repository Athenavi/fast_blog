<script lang="ts" setup>
const {t} = useI18n()
/**
 * 文章管理（列表）
 *
 * 对齐 v3：`/content/article`。本页只负责「找文章 + 批量处理」，
 * 编辑在独立页面 `/content/article/[id]`（`new` 表示新建），带富文本与预览。
 *
 * 列表骨架（筛选 / 批量条 / 空态 / 骨架屏 / 分页 / URL 同步）来自
 * `AdminListShell` + `useAdminList`，页面只声明列与动作。
 */
import {Delete, Edit, Plus, Star, Top, View} from '@element-plus/icons-vue'
import {ref} from 'vue'

import {articleApi, type ArticleItem, type ArticleQuery} from '@/api'
import {useAdminList} from '@/composables/useAdminList'
import {useCategoryOptions} from '@/composables/useCategoryOptions'
import {ElMessage} from '@/utils/feedback'
import {articleStatusKey, articleStatusTag, formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.article.management',
  permission: 'module_content:article:view',
})

const router = useRouter()

/** 排序选项的值形如 `字段:方向`，切换后拆进查询参数 */
const SORT_OPTIONS = computed(() => [
  {label: t('admin.content.article.sortUpdatedDesc'), value: 'updated_at:desc'},
  {label: t('admin.content.article.sortCreatedDesc'), value: 'created_at:desc'},
  {label: t('admin.content.article.sortViewsDesc'), value: 'views:desc'},
  {label: t('admin.content.article.sortSortOrder'), value: 'sort_order:asc'},
])

const STATUS_OPTIONS = computed(() => [
  {label: t('common.published'), value: 1},
  {label: t('common.draft'), value: 0},
])

const list = useAdminList<ArticleItem, ArticleQuery>({
  fetcher: (params) => articleApi.list(params),
  defaultQuery: {
    keyword: '',
    status: undefined,
    category_id: undefined,
    order_by: undefined,
    order: undefined,
  },
  syncUrl: true,
})

const {categories, nameOf: categoryName} = useCategoryOptions()
const sortValue = ref('updated_at:desc')

function onSortChange(value: string): void {
  const [orderBy, order] = value.split(':')
  list.query.order_by = orderBy
  list.query.order = order as 'asc' | 'desc'
  void list.search()
}

// ---------------------------------------------------------------- 导航与行操作
function openCreate(): void {
  void router.push('/content/article/new')
}

function openEdit(row: ArticleItem): void {
  void router.push(`/content/article/${row.id}`)
}

/** 预览走前台详情路由（`/articles/id/{id}` 不依赖 slug，草稿也能看） */
function preview(row: ArticleItem): void {
  window.open(`/articles/id/${row.id}`, '_blank', 'noopener')
}

async function togglePublish(row: ArticleItem): Promise<void> {
  const next = row.status !== 1
  await articleApi.publish(row.id, next)
  ElMessage.success(next ? t('common.published') : t('admin.content.article.movedToDraft'))
  await list.reload()
}

async function removeRow(row: ArticleItem): Promise<void> {
  await list.remove(
    () => articleApi.remove(row.id),
    t('admin.content.article.deleteConfirm', {title: row.title ?? row.id}),
    t('admin.common.notice'),
    t('admin.content.article.deleted'),
  )
}

// ---------------------------------------------------------------- 批量操作
/** 批量发布/下架：后端没有批量端点，这里逐条真实调用并如实汇报失败数 */
async function bulkPublish(publish: boolean): Promise<void> {
  if (!list.selectedCount.value) {
    ElMessage.warning(t('admin.content.article.selectFirst'))
    return
  }
  const ids = [...list.selectedIds.value]
  const result = await articleApi.batchPublish(ids, publish)
  ElMessage.success(t('admin.common.batchDone', {n: result.affected}))
  await list.reload()
}

async function bulkDelete(): Promise<void> {
  if (!list.selectedCount.value) {
    ElMessage.warning(t('admin.content.article.selectFirst'))
    return
  }
  const ids = [...list.selectedIds.value]
  await list.remove(
    () => articleApi.batchDelete(ids),
    t('admin.content.article.deleteSelectedConfirm', {n: ids.length}),
    t('admin.common.notice'),
    t('admin.content.article.deleted'),
  )
}

</script>

<template>
  <AdminPage :desc="$t('admin.content.article.desc')" :title="$t('admin.content.article.management')">
    <template #actions>
      <el-button v-auth="'module_content:article:create'" :icon="Plus" type="primary" @click="openCreate">
        {{ $t('admin.content.article.newArticle') }}
      </el-button>
    </template>

    <AdminListShell
      :empty-desc="list.hasFilters.value ? $t('admin.content.article.emptyFiltered') : $t('admin.content.article.emptyDesc')"
      :empty-title="list.hasFilters.value ? $t('admin.content.article.emptyFiltered') : $t('admin.content.article.emptyTitle')"
      :failed="list.failed.value"
      :loading="list.loading.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      :rows="list.rows.value"
      :selection-count="list.selectedCount.value"
      :total="list.total.value"
      @refresh="list.reload"
      @reset="list.reset"
      @search="list.search"
      @clear-selection="list.clearSelection"
      @page-change="list.onPageChange"
      @selection-change="list.onSelectionChange"
      @size-change="list.onSizeChange"
    >
      <template #filters>
        <el-form-item :label="$t('admin.content.article.keyword')">
          <el-input
            v-model="list.query.keyword"
            :placeholder="$t('admin.content.article.titleKeyword')"
            clearable
            style="width: 200px"
            @keyup.enter="list.search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="list.query.status" :placeholder="$t('admin.common.all')" clearable style="width: 130px">
            <el-option v-for="item in STATUS_OPTIONS" :key="item.value" :label="item.label" :value="item.value"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.content.article.category')">
          <el-select
            v-model="list.query.category_id"
            :placeholder="$t('admin.content.article.allCategories')"
            clearable
            style="width: 160px"
          >
            <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.content.article.sort')">
          <el-select v-model="sortValue" style="width: 150px" @change="onSortChange">
            <el-option v-for="item in SORT_OPTIONS" :key="item.value" :label="item.label" :value="item.value"/>
          </el-select>
        </el-form-item>
      </template>

      <template #bulk>
        <el-button v-auth="'module_content:article:edit'" plain type="primary" @click="bulkPublish(true)">
          {{ $t('admin.content.article.batchPublish') }}
        </el-button>
        <el-button v-auth="'module_content:article:edit'" plain @click="bulkPublish(false)">
          {{ $t('admin.content.article.batchUnpublish') }}
        </el-button>
        <el-button v-auth="'module_content:article:delete'" plain type="danger" @click="bulkDelete">
          {{ $t('admin.common.delete') }}
        </el-button>
      </template>

      <template #empty-actions>
        <el-button v-auth="'module_content:article:create'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.content.article.newArticle') }}
        </el-button>
      </template>

      <el-table-column width="72">
        <template #default="{row}">
          <img v-if="row.cover_image" :src="row.cover_image" alt="" class="admin-thumb" decoding="async"
               loading="lazy"/>
          <span v-else class="admin-thumb admin-thumb--empty"/>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.content.article.articleTitle')" min-width="280">
        <template #default="{row}">
          <div class="admin-cell-title">{{ row.title }}</div>
          <div class="admin-cell-sub">
            <span v-if="row.slug">/{{ row.slug }}</span>
            <span v-else>{{ row.excerpt ? row.excerpt.slice(0, 60) : '—' }}</span>
          </div>
          <div class="article-flags">
            <el-tag v-if="row.is_sticky" :icon="Top" size="small" type="warning">
              {{ $t('admin.content.article.featured') }}
            </el-tag>
            <el-tag v-if="row.is_featured" :icon="Star" size="small" type="success">
              {{ $t('admin.content.article.recommended') }}
            </el-tag>
            <el-tag v-if="row.is_vip_only" size="small" type="danger">
              {{ $t('admin.content.article.vipOnly') }}
            </el-tag>
            <el-tag v-if="row.hidden" size="small" type="info">
              {{ $t('admin.content.article.hidden') }}
            </el-tag>
          </div>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.content.article.category')" width="140">
        <template #default="{row}">{{ categoryName(row.category_id) }}</template>
      </el-table-column>

      <el-table-column :label="$t('admin.common.status')" width="120">
        <template #default="{row}">
          <el-tag :type="articleStatusTag(row.status)" size="small">
            {{ $t(`common.${articleStatusKey(row.status)}`) }}
          </el-tag>
          <el-tag v-if="row.scheduled_publish_at" class="flag-gap" size="small" type="info">
            {{ $t('admin.content.article.scheduledPublish') }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.content.article.views')" prop="views" sortable="custom" width="100"/>
      <el-table-column :label="$t('admin.content.article.likes')" prop="likes" width="90"/>

      <el-table-column :label="$t('admin.common.updatedAt')" width="170">
        <template #default="{row}">{{ formatDateTime(row.updated_at) }}</template>
      </el-table-column>

      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="260">
        <template #default="{row}">
          <el-button v-auth="'module_content:article:edit'" :icon="Edit" link type="primary"
                     @click="openEdit(row as ArticleItem)">
            {{ $t('admin.common.edit') }}
          </el-button>
          <el-button :icon="View" link @click="preview(row as ArticleItem)">
            {{ $t('admin.content.article.preview') }}
          </el-button>
          <el-button v-auth="'module_content:article:edit'" link type="primary"
                     @click="togglePublish(row as ArticleItem)">
            {{ row.status === 1 ? $t('admin.content.article.moveToDraft') : $t('admin.content.article.publish') }}
          </el-button>
          <el-button v-auth="'module_content:article:delete'" :icon="Delete" link type="danger"
                     @click="removeRow(row as ArticleItem)">
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>
  </AdminPage>
</template>

<style scoped>
.admin-thumb--empty {
  display: inline-block;
}

.article-flags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.flag-gap {
  margin-left: 4px;
}
</style>
