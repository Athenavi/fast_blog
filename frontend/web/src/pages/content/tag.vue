<script lang="ts" setup>
const {t} = useI18n()
/**
 * 标签管理
 *
 * 标签不单独建表——存在 `articles.tags_list`(JSON) 里，因此后端只提供
 * 「聚合列表 / 重命名（同名即合并）/ 删除」：
 *  - 重命名：点击标签名就地编辑，回车提交；目标名已存在时后端会**合并**（`merged: true`）；
 *  - 查看文章：抽屉里按标签查文章（`/content/tag/{tag}/articles`）；
 *  - 排序：后端按文章数聚合返回，这里支持"按文章数 / 按名称"切换（前端排序当前页）。
 */
import {Delete, Document, Edit, Refresh} from '@element-plus/icons-vue'
import {computed, ref} from 'vue'

import {tagApi, type TagItem} from '@/api'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {articleStatusKey, articleStatusTag, formatDateTime, truncate} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.tag.tagManagement',
  permission: 'module_content:tag:view',
})

type TagQuery = { keyword?: string; min_count?: number }

const list = useAdminList<TagItem, TagQuery>({
  fetcher: (params) => tagApi.list(params),
  defaultQuery: {keyword: '', min_count: undefined},
  pageSize: 50,
  rowKey: 'name',
  syncUrl: true,
})

const sortBy = ref<'count' | 'name'>('count')
const sortedRows = computed(() => {
  const rows = [...list.rows.value]
  return sortBy.value === 'name'
    ? rows.sort((a, b) => a.name.localeCompare(b.name))
    : rows.sort((a, b) => b.count - a.count)
})

// ---------------------------------------------------------------- 内联重命名（同名即合并）
const editingTag = ref<string | null>(null)
const draftName = ref('')

function startEdit(tag: TagItem): void {
  editingTag.value = tag.name
  draftName.value = tag.name
}

function cancelEdit(): void {
  editingTag.value = null
  draftName.value = ''
}

async function commitEdit(): Promise<void> {
  const from = editingTag.value
  const to = draftName.value.trim()
  if (from === null || !to || to === from) {
    cancelEdit()
    return
  }
  const result = await tagApi.rename(from, to)
  ElMessage.success(
    result.merged ? t('admin.content.tag.mergedIntoTheSameNameTag') : t('admin.content.tag.renamed'),
  )
  cancelEdit()
  await list.reload()
}

// ---------------------------------------------------------------- 删除
async function removeTag(tag: TagItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.content.tag.deleteConfirm', {name: tag.name, count: tag.count}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await tagApi.remove(tag.name)
  ElMessage.success(t('admin.content.tag.deleted'))
  await list.reload()
}

// ---------------------------------------------------------------- 查看文章
const articlesVisible = ref(false)
const articlesTag = ref<string | null>(null)
const articlesLoading = ref(false)
const articles = ref<Array<Record<string, unknown>>>([])

async function openArticles(tag: TagItem): Promise<void> {
  articlesTag.value = tag.name
  articlesVisible.value = true
  articlesLoading.value = true
  try {
    const result = await tagApi.articles(tag.name, {page: 1, page_size: 50})
    articles.value = (result.items ?? []) as Array<Record<string, unknown>>
  } catch {
    articles.value = []
  } finally {
    articlesLoading.value = false
  }
}

function articleTitle(row: Record<string, unknown>): string {
  return String(row.title ?? `#${String(row.id ?? '')}`)
}

function articleId(row: Record<string, unknown>): number {
  return Number(row.id ?? 0)
}

function openArticle(row: Record<string, unknown>): void {
  const id = articleId(row)
  if (id) window.open(`/articles/id/${id}`, '_blank', 'noopener')
}
</script>

<template>
  <AdminPage :desc="$t('admin.content.tag.desc')" :title="$t('admin.content.tag.tagManagement')">
    <AdminListShell
      :empty-desc="list.hasFilters.value ? $t('admin.content.tag.emptyFiltered') : $t('admin.content.tag.emptyDesc')"
      :empty-title="list.hasFilters.value ? $t('admin.content.tag.emptyFiltered') : $t('admin.content.tag.emptyTitle')"
      :failed="list.failed.value"
      :loading="list.loading.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      :rows="sortedRows"
      :selectable="false"
      :total="list.total.value"
      @refresh="list.reload"
      @reset="list.reset"
      @search="list.search"
      @page-change="list.onPageChange"
      @size-change="list.onSizeChange"
    >
      <template #filters>
        <el-form-item :label="$t('admin.content.tag.keyword')">
          <el-input
            v-model="list.query.keyword"
            :placeholder="$t('admin.content.tag.tagNameContains')"
            clearable
            style="width: 200px"
            @keyup.enter="list.search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.content.tag.minimumArticleCount')">
          <el-input-number v-model="list.query.min_count" :controls="false" :min="1" style="width: 120px"
                           @change="list.search()"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.tag.sortBy')">
          <el-radio-group v-model="sortBy">
            <el-radio-button value="count">{{ $t('admin.content.tag.sortByCount') }}</el-radio-button>
            <el-radio-button value="name">{{ $t('admin.content.tag.sortByName') }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </template>

      <template #actions>
        <el-button :icon="Refresh" @click="list.reload()">{{ $t('admin.common.refresh') }}</el-button>
      </template>

      <el-table-column :label="$t('admin.content.tag.newTag')" min-width="280">
        <template #default="{row}">
          <el-input
            v-if="editingTag === row.name"
            v-model="draftName"
            class="tag-inline"
            maxlength="60"
            size="small"
            @blur="commitEdit"
            @keyup.enter="commitEdit"
            @keyup.esc="cancelEdit"
          />
          <template v-else>
            <button class="tag-name" type="button" @click="startEdit(row as TagItem)">
              {{ row.name }}
            </button>
          </template>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.content.tag.articleCount')" prop="count" width="120">
        <template #default="{row}">
          <el-tag size="small" type="info">{{ row.count }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="220">
        <template #default="{row}">
          <el-button :icon="Document" link type="primary" @click="openArticles(row as TagItem)">
            {{ $t('admin.content.tag.viewArticles') }}
          </el-button>
          <el-button v-auth="'module_content:tag:edit'" :icon="Edit" link @click="startEdit(row as TagItem)">
            {{ $t('admin.content.tag.rename') }}
          </el-button>
          <el-button v-auth="'module_content:tag:delete'" :icon="Delete" link type="danger"
                     @click="removeTag(row as TagItem)">
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>

    <!-- 该标签下的文章 -->
    <el-drawer v-model="articlesVisible" :size="560"
               :title="$t('admin.content.tag.articlesTitle', {name: articlesTag ?? ''})">
      <div v-loading="articlesLoading">
        <AdminEmpty v-if="!articlesLoading && !articles.length" :title="$t('admin.content.tag.noArticles')"/>
        <ul v-else class="tag-articles">
          <li v-for="row in articles" :key="articleId(row)" class="tag-articles__item">
            <div class="tag-articles__main">
              <button class="tag-articles__title" type="button" @click="openArticle(row)">
                {{ articleTitle(row) }}
              </button>
              <div class="admin-cell-sub">{{ truncate(String(row.excerpt ?? ''), 80) }}</div>
            </div>
            <el-tag :type="articleStatusTag(Number(row.status ?? 0))" size="small">
              {{ $t(`common.${articleStatusKey(Number(row.status ?? 0))}`) }}
            </el-tag>
            <span class="tag-articles__time">{{ formatDateTime(String(row.updated_at ?? '')) }}</span>
          </li>
        </ul>
      </div>
    </el-drawer>
  </AdminPage>
</template>

<style scoped>
.tag-inline {
  width: 220px;
}

.tag-name {
  padding: 0;
  border: none;
  background: none;
  font: inherit;
  font-weight: 500;
  color: var(--admin-fg);
  cursor: text;
}

.tag-name:hover {
  color: var(--admin-primary);
}

.tag-articles {
  margin: 0;
  padding: 0;
  list-style: none;
}

.tag-articles__item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--admin-line);
}

.tag-articles__main {
  flex: 1 1 auto;
  min-width: 0;
}

.tag-articles__title {
  padding: 0;
  border: none;
  background: none;
  font: inherit;
  font-weight: 500;
  color: var(--admin-fg);
  text-align: left;
  cursor: pointer;
}

.tag-articles__title:hover {
  color: var(--admin-primary);
}

.tag-articles__time {
  font-size: 12px;
  color: var(--admin-fg-subtle);
}
</style>
