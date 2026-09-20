<script lang="ts" setup>
/**
 * 页面搭建管理
 *
 * 对齐 v3 `/content/page-builder`（slug 创建后锁定，唯一冲突 409 由请求拦截器统一提示）。
 * 页面骨架与 system/sensitive-words 页一致：搜索区 + 表格 + 抽屉表单。
 * v1 不做可视化拖拽（可视化编辑器二期），抽屉内提供结构化块管理 + 源码模式两种编辑方式。
 */
import {Bottom, Delete, EditPen, Plus, Refresh, Search, Top} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

// 临时直接从模块导入（api/index.ts 聚合导出由主 agent 统一登记）
import {pageBuilderApi, type PageBuilderItem} from '@/api/modules/pageBuilder'
import type {PageQuery} from '@/api/types'
import {useTable} from '@/hooks/useTable'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.pageBuilder.title',
  permission: 'module_content:page_builder:view',
})

const {t} = useI18n()

interface PageBuilderQueryForm extends PageQuery {
  keyword?: string
  is_published?: boolean
}

const {
  list,
  loading,
  total,
  page,
  pageSize,
  query,
  search,
  reset,
  load,
  onPageChange,
  onSizeChange,
} = useTable<PageBuilderItem, PageBuilderQueryForm>({
  fetcher: (params) => pageBuilderApi.list(params),
  defaultQuery: {keyword: '', is_published: undefined},
})

// ---- 新建 / 编辑 ----
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)

/** 块对象（后端契约：blocks_data 为对象数组，块类型取 block.type，缺失显示 unknown） */
type PageBlock = Record<string, unknown>

const form = reactive<{
  title: string;
  slug: string;
  template_name: string;
  is_published: boolean;
  blocks: PageBlock[]
}>({
  title: '',
  slug: '',
  template_name: '',
  is_published: true,
  blocks: [],
})

const formTitle = computed(() => (editingId.value ? t('admin.content.pageBuilder.editTitle') : t('admin.content.pageBuilder.createTitle')))

function openCreate() {
  editingId.value = null
  Object.assign(form, {title: '', slug: '', template_name: '', is_published: true, blocks: []})
  blocksMode.value = 'list'
  formVisible.value = true
}

function openEdit(row: PageBuilderItem) {
  editingId.value = row.id
  Object.assign(form, {
    title: row.title ?? '',
    slug: row.slug ?? '',
    template_name: row.template_name ?? '',
    is_published: row.is_published,
    blocks: Array.isArray(row.blocks_data) ? [...row.blocks_data] : [],
  })
  blocksMode.value = 'list'
  formVisible.value = true
}

async function submitForm() {
  if (!form.title.trim()) {
    ElMessage.warning(t('admin.content.pageBuilder.titleRequired'))
    return
  }
  if (!editingId.value && !form.slug.trim()) {
    ElMessage.warning(t('admin.content.pageBuilder.slugRequired'))
    return
  }
  // 源码模式下若未应用成功则阻断提交
  if (blocksMode.value === 'source' && !applySource()) {
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      // 更新契约：不携带 slug（创建后锁定）
      await pageBuilderApi.update(editingId.value, {
        title: form.title.trim(),
        blocks_data: form.blocks,
        template_name: form.template_name.trim() || null,
        is_published: form.is_published,
      })
    } else {
      await pageBuilderApi.create({
        title: form.title.trim(),
        slug: form.slug.trim(),
        blocks_data: form.blocks,
        template_name: form.template_name.trim() || null,
        is_published: form.is_published,
      })
    }
    ElMessage.success(t('admin.common.save'))
    formVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(row: PageBuilderItem) {
  await ElMessageBox.confirm(
    t('admin.content.pageBuilder.deleteConfirm', {name: row.title || row.slug}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await pageBuilderApi.remove(row.id)
  ElMessage.success(t('admin.common.delete'))
  await load()
}

async function togglePublish(row: PageBuilderItem) {
  await pageBuilderApi.publish(row.id, !row.is_published)
  await load()
}

// ---- 块编辑（结构化 / 源码两种模式） ----
const blocksMode = ref<'list' | 'source'>('list')
const blocksSource = ref('')

function blockCount(row: PageBuilderItem): number {
  return Array.isArray(row.blocks_data) ? row.blocks_data.length : 0
}

function blockTypeOf(block: PageBlock | null | undefined): string {
  const value = block?.['type']
  return typeof value === 'string' && value.trim() ? value.trim() : 'unknown'
}

function moveBlock(index: number, offset: -1 | 1) {
  const target = index + offset
  if (target < 0 || target >= form.blocks.length) return
  const [moved] = form.blocks.splice(index, 1)
  if (moved) form.blocks.splice(target, 0, moved)
}

function removeBlock(index: number) {
  form.blocks.splice(index, 1)
}

function onBlocksModeChange(mode: string | number | boolean | undefined) {
  if (mode === 'source') {
    blocksSource.value = JSON.stringify(form.blocks, null, 2)
    blocksMode.value = 'source'
    return
  }
  // 切回结构化：先应用源码，失败则停留并提示
  if (applySource()) {
    blocksMode.value = 'list'
  }
}

/** 应用源码 textarea 的 JSON 到 blocks；失败返回 false（ ElMessage 警告） */
function applySource(): boolean {
  try {
    const parsed: unknown = JSON.parse(blocksSource.value)
    if (!Array.isArray(parsed)) {
      ElMessage.warning(t('admin.content.pageBuilder.blocksMustBeArray'))
      return false
    }
    if (parsed.some((item) => typeof item !== 'object' || item === null || Array.isArray(item))) {
      ElMessage.warning(t('admin.content.pageBuilder.blockMustBeObject'))
      return false
    }
    form.blocks = parsed as PageBlock[]
    return true
  } catch (error) {
    ElMessage.warning(t('admin.common.configInvalidJson', {message: (error as Error).message}))
    return false
  }
}

// ---- 添加 / 编辑单块弹窗 ----
const blockDialogVisible = ref(false)
const blockEditingIndex = ref<number | null>(null)
const blockForm = reactive<{ type: string; content: string }>({type: '', content: ''})

const blockDialogTitle = computed(() =>
  blockEditingIndex.value === null
    ? t('admin.content.pageBuilder.addBlock')
    : t('admin.content.pageBuilder.editBlockTitle'),
)

function openAddBlock() {
  blockEditingIndex.value = null
  blockForm.type = ''
  blockForm.content = ''
  blockDialogVisible.value = true
}

function openEditBlock(index: number) {
  const block = form.blocks[index]
  if (!block) return
  blockEditingIndex.value = index
  blockForm.type = blockTypeOf(block)
  blockForm.content = JSON.stringify(block, null, 2)
  blockDialogVisible.value = true
}

function saveBlock() {
  if (!blockForm.type.trim()) {
    ElMessage.warning(t('admin.content.pageBuilder.blockTypeRequired'))
    return
  }
  let content: PageBlock = {}
  const text = blockForm.content.trim()
  if (text) {
    try {
      const parsed: unknown = JSON.parse(text)
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        ElMessage.warning(t('admin.content.pageBuilder.blockMustBeObject'))
        return
      }
      content = parsed as PageBlock
    } catch (error) {
      ElMessage.warning(t('admin.common.configInvalidJson', {message: (error as Error).message}))
      return
    }
  }
  const block: PageBlock = {...content, type: blockForm.type.trim()}
  if (blockEditingIndex.value === null) {
    form.blocks.push(block)
  } else {
    form.blocks.splice(blockEditingIndex.value, 1, block)
  }
  blockDialogVisible.value = false
}
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <!-- 搜索区 -->
      <el-form :inline="true" :model="query" @submit.prevent="search()">
        <el-form-item :label="$t('admin.content.pageBuilder.keyword')">
          <el-input
            v-model="query.keyword"
            :placeholder="$t('admin.content.pageBuilder.keywordPlaceholder')"
            clearable
            style="width: 200px"
            @keyup.enter="search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.content.pageBuilder.isPublished')">
          <el-select v-model="query.is_published" :placeholder="$t('admin.common.all')" clearable style="width: 120px">
            <el-option :label="$t('admin.content.pageBuilder.published')" :value="true"/>
            <el-option :label="$t('admin.content.pageBuilder.unpublished')" :value="false"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="search()">{{ $t('admin.common.search') }}</el-button>
          <el-button :icon="Refresh" @click="reset()">{{ $t('admin.common.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <!-- 操作区 -->
      <div class="table-toolbar">
        <el-button v-auth="'module_content:page_builder:create'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.content.pageBuilder.createTitle') }}
        </el-button>
        <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: total}) }}</span>
      </div>

      <!-- 表格 -->
      <el-table v-loading="loading" :data="list" border stripe>
        <el-table-column :label="$t('admin.content.pageBuilder.pageTitle')" min-width="160" prop="title"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.content.pageBuilder.slug')" min-width="140" prop="slug"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.content.pageBuilder.templateName')" min-width="120" prop="template_name"
                         show-overflow-tooltip>
          <template #default="{ row }">
            {{ (row as PageBuilderItem).template_name || $t('admin.content.pageBuilder.templateDefault') }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.content.pageBuilder.blockCount')" align="center" width="90">
          <template #default="{ row }">{{ blockCount(row as PageBuilderItem) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="(row as PageBuilderItem).is_published ? 'success' : 'info'" size="small">
              {{
                (row as PageBuilderItem).is_published ? $t('admin.content.pageBuilder.published') : $t('admin.content.pageBuilder.unpublished')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="210">
          <template #default="{ row }">
            <el-button v-auth="'module_content:page_builder:edit'" link type="primary"
                       @click="openEdit(row as PageBuilderItem)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button
              v-auth="'module_content:page_builder:edit'"
              :type="(row as PageBuilderItem).is_published ? 'warning' : 'success'"
              link
              @click="togglePublish(row as PageBuilderItem)"
            >
              {{
                (row as PageBuilderItem).is_published ? $t('admin.content.pageBuilder.unpublish') : $t('admin.content.pageBuilder.publish')
              }}
            </el-button>
            <el-button v-auth="'module_content:page_builder:delete'" link type="danger"
                       @click="onDelete(row as PageBuilderItem)">
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        background
        class="table-pagination"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </el-card>

    <!-- 新建 / 编辑 -->
    <el-drawer v-model="formVisible" :title="formTitle" destroy-on-close size="560px">
      <el-form :model="form" label-width="90px">
        <el-form-item :label="$t('admin.content.pageBuilder.pageTitle')" required>
          <el-input v-model="form.title" :placeholder="$t('admin.content.pageBuilder.pageTitlePlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.pageBuilder.slug')" required>
          <el-input v-model="form.slug" :disabled="editingId !== null"
                    :placeholder="$t('admin.content.pageBuilder.slugPlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.pageBuilder.templateName')">
          <el-input v-model="form.template_name"
                    :placeholder="$t('admin.content.pageBuilder.templateNamePlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.pageBuilder.isPublished')">
          <el-switch v-model="form.is_published"/>
        </el-form-item>

        <!-- blocks 编辑区：结构化列表 / 源码 JSON -->
        <el-form-item :label="$t('admin.content.pageBuilder.blocks')">
          <div class="blocks-editor">
            <div class="blocks-editor__toolbar">
              <el-radio-group :model-value="blocksMode" size="small" @change="onBlocksModeChange">
                <el-radio-button value="list">{{ $t('admin.content.pageBuilder.modeStructured') }}</el-radio-button>
                <el-radio-button value="source">{{ $t('admin.content.pageBuilder.modeSource') }}</el-radio-button>
              </el-radio-group>
              <el-button v-if="blocksMode === 'list'" :icon="Plus" size="small" type="primary" @click="openAddBlock">
                {{ $t('admin.content.pageBuilder.addBlock') }}
              </el-button>
              <el-button v-else size="small" type="primary" @click="applySource">
                {{ $t('admin.content.pageBuilder.apply') }}
              </el-button>
            </div>

            <template v-if="blocksMode === 'list'">
              <div v-if="!form.blocks.length" class="blocks-editor__empty">
                {{ $t('admin.content.pageBuilder.blocksEmpty') }}
              </div>
              <div v-for="(block, index) in form.blocks" :key="index" class="blocks-editor__row">
                <span class="blocks-editor__index">{{ index + 1 }}</span>
                <el-tag size="small">{{ blockTypeOf(block) }}</el-tag>
                <span class="blocks-editor__ops">
                  <el-button v-if="index > 0" :icon="Top" :title="$t('admin.content.pageBuilder.moveUp')"
                             link size="small" @click="moveBlock(index, -1)"/>
                  <el-button v-if="index < form.blocks.length - 1" :icon="Bottom"
                             :title="$t('admin.content.pageBuilder.moveDown')" link size="small"
                             @click="moveBlock(index, 1)"/>
                  <el-button :icon="EditPen" :title="$t('admin.content.pageBuilder.editBlockTitle')" link size="small"
                             type="primary" @click="openEditBlock(index)"/>
                  <el-button :icon="Delete" :title="$t('admin.common.delete')" link size="small" type="danger"
                             @click="removeBlock(index)"/>
                </span>
              </div>
            </template>
            <el-input
              v-else
              v-model="blocksSource"
              :autosize="{minRows: 8, maxRows: 18}"
              :placeholder="$t('admin.content.pageBuilder.sourcePlaceholder')"
              class="blocks-editor__source"
              type="textarea"
            />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-drawer>

    <!-- 添加 / 编辑块 -->
    <el-dialog v-model="blockDialogVisible" :title="blockDialogTitle" append-to-body width="560px">
      <el-form label-width="110px">
        <el-form-item :label="$t('admin.content.pageBuilder.blockType')" required>
          <el-input v-model="blockForm.type" :placeholder="$t('admin.content.pageBuilder.blockTypePlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.pageBuilder.blockContent')">
          <el-input
            v-model="blockForm.content"
            :autosize="{minRows: 6, maxRows: 14}"
            :placeholder="$t('admin.content.pageBuilder.blockContentPlaceholder')"
            type="textarea"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="blockDialogVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button type="primary" @click="saveBlock">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.blocks-editor {
  width: 100%;
}

.blocks-editor__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.blocks-editor__empty {
  padding: 16px 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  text-align: center;
}

.blocks-editor__row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  margin-bottom: 6px;
}

.blocks-editor__index {
  min-width: 20px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  text-align: center;
}

.blocks-editor__ops {
  display: flex;
  align-items: center;
  margin-left: auto;
}

.blocks-editor__source {
  width: 100%;
}
</style>
