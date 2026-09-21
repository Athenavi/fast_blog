<script lang="ts" setup>
/**
 * 区块模板库（T5-11 批次 1）
 *
 * 对齐 v3 `/extension/block-pattern`：`blocks` 列存编辑器 JSON。
 */
import {Plus} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {blockPatternApi, type BlockPatternItem} from '@/api'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.extension.blockPattern.title',
  permission: 'module_extension:block_pattern:view',
})

const {t} = useI18n()

const patternState = useAdminList<BlockPatternItem, { keyword?: string; category?: string }>({
  fetcher: (params) => blockPatternApi.list(params),
  defaultQuery: {keyword: '', category: ''},
  syncUrl: true,
})

// 模板沿用原有变量名：映射为同名 ref / 函数，避免整页重写带来的回归风险
const list = patternState.rows
const loading = patternState.loading
const failed = patternState.failed
const total = patternState.total
const page = patternState.page
const pageSize = patternState.pageSize
const query = patternState.query
const search = patternState.search
const reset = patternState.reset
const load = patternState.reload
const onPageChange = patternState.onPageChange
const onSizeChange = patternState.onSizeChange

const formVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({
  name: '', title: '', description: '', category: '', blocks: '', keywords: '', is_public: false,
})

const formTitle = computed(() =>
  editingId.value ? t('admin.extension.blockPattern.editTitle') : t('admin.extension.blockPattern.createTitle'))

function openCreate() {
  editingId.value = null
  Object.assign(form, {name: '', title: '', description: '', category: '', blocks: '', keywords: '', is_public: false})
  formVisible.value = true
}

function openEdit(row: BlockPatternItem) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name || '',
    title: row.title || '',
    description: row.description || '',
    category: row.category || '',
    blocks: row.blocks || '',
    keywords: row.keywords || '',
    is_public: row.is_public,
  })
  formVisible.value = true
}

async function submitForm() {
  if (!form.name.trim() || !form.title.trim()) {
    ElMessage.warning(t('admin.extension.blockPattern.nameRequired'))
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      title: form.title.trim(),
      description: form.description || null,
      category: form.category || null,
      blocks: form.blocks || null,
      keywords: form.keywords || null,
      is_public: form.is_public,
    }
    if (editingId.value) {
      await blockPatternApi.update(editingId.value, payload)
    } else {
      await blockPatternApi.create(payload)
    }
    ElMessage.success(t('admin.common.save'))
    formVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(row: BlockPatternItem) {
  await ElMessageBox.confirm(t('admin.extension.blockPattern.deleteConfirm'), t('admin.common.notice'), {type: 'warning'})
  await blockPatternApi.remove(row.id)
  ElMessage.success(t('admin.common.delete'))
  await load()
}
</script>

<template>
  <AdminPage :desc="$t('admin.extension.blockPattern.desc')" :title="$t('admin.extension.blockPattern.title')">
    <AdminListShell
      :empty-desc="patternState.hasFilters.value
        ? $t('admin.extension.blockPattern.emptyFiltered')
        : $t('admin.extension.blockPattern.emptyDesc')"
      :empty-title="$t('admin.extension.blockPattern.emptyTitle')"
      :failed="failed"
      :loading="loading"
      :page="page"
      :page-size="pageSize"
      :rows="list"
      :selectable="false"
      :total="total"
      @refresh="load()"
      @reset="reset()"
      @search="search()"
      @page-change="onPageChange"
      @size-change="onSizeChange"
    >
      <template #filters>
        <el-form-item :label="$t('admin.extension.blockPattern.keyword')">
          <el-input v-model="query.keyword" clearable style="width: 180px" @keyup.enter="search()"/>
        </el-form-item>
        <el-form-item :label="$t('admin.extension.blockPattern.category')">
          <el-input v-model="query.category" clearable style="width: 140px"/>
        </el-form-item>
      </template>

      <template #actions>
        <el-button v-auth="'module_extension:block_pattern:create'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.extension.blockPattern.createTitle') }}
        </el-button>
      </template>

        <el-table-column :label="$t('admin.extension.blockPattern.blockTitle')" min-width="160" prop="title"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.extension.blockPattern.blockName')" min-width="120" prop="name"
                         show-overflow-tooltip/>
      <el-table-column :label="$t('admin.extension.blockPattern.category')" prop="category" width="110"/>
        <el-table-column :label="$t('admin.extension.blockPattern.keywords')" min-width="140" prop="keywords"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.common.status')" width="90">
          <template #default="{ row }">
            <el-tag :type="(row as BlockPatternItem).is_public ? 'success' : 'info'" size="small">
              {{
                (row as BlockPatternItem).is_public ? $t('admin.extension.blockPattern.public') : $t('admin.extension.blockPattern.private')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
          <template #default="{ row }">
            <el-button v-auth="'module_extension:block_pattern:edit'" link type="primary"
                       @click="openEdit(row as BlockPatternItem)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button v-auth="'module_extension:block_pattern:delete'" link type="danger"
                       @click="onDelete(row as BlockPatternItem)">
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
    </AdminListShell>

    <el-drawer v-model="formVisible" :title="formTitle" destroy-on-close size="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item :label="$t('admin.extension.blockPattern.blockName')" required>
          <el-input v-model="form.name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.extension.blockPattern.blockTitle')" required>
          <el-input v-model="form.title"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description"/>
        </el-form-item>
        <el-form-item :label="$t('admin.extension.blockPattern.category')">
          <el-input v-model="form.category"/>
        </el-form-item>
        <el-form-item :label="$t('admin.extension.blockPattern.keywords')">
          <el-input v-model="form.keywords"/>
        </el-form-item>
        <el-form-item :label="$t('admin.extension.blockPattern.blocks')">
          <el-input v-model="form.blocks" :autosize="{minRows: 6, maxRows: 14}" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="form.is_public"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-drawer>
  </AdminPage>
</template>
