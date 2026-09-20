<script lang="ts" setup>
/**
 * 短代码管理
 *
 * 对齐 v3 `/content/shortcode`（code 创建后锁定，重复 409 由请求拦截器统一提示）。
 * 页面骨架与 system/sensitive-words 页一致：搜索区 + 表格 + 抽屉表单。
 */
import {CopyDocument, Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {shortcodeApi, type ShortcodeItem, type ShortcodeQuery} from '@/api'
import {useTable} from '@/hooks/useTable'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.shortcode.title',
  permission: 'module_content:shortcode:view',
})

const {t} = useI18n()

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
} = useTable<ShortcodeItem, ShortcodeQuery>({
  fetcher: (params) => shortcodeApi.list(params),
  defaultQuery: {keyword: '', is_active: undefined},
})

// ---- 新建 / 编辑 ----
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive<{
  code: string;
  name: string;
  description: string;
  content: string;
  is_active: boolean
}>({
  code: '',
  name: '',
  description: '',
  content: '',
  is_active: true,
})

const formTitle = computed(() => (editingId.value ? t('admin.content.shortcode.editTitle') : t('admin.content.shortcode.createTitle')))

function openCreate() {
  editingId.value = null
  Object.assign(form, {code: '', name: '', description: '', content: '', is_active: true})
  formVisible.value = true
}

function openEdit(row: ShortcodeItem) {
  editingId.value = row.id
  Object.assign(form, {
    code: row.code,
    name: row.name,
    description: row.description || '',
    content: row.content,
    is_active: row.is_active,
  })
  formVisible.value = true
}

async function submitForm() {
  if (!editingId.value && !form.code.trim()) {
    ElMessage.warning(t('admin.content.shortcode.codeRequired'))
    return
  }
  if (!form.name.trim()) {
    ElMessage.warning(t('admin.content.shortcode.nameRequired'))
    return
  }
  if (!form.content.trim()) {
    ElMessage.warning(t('admin.content.shortcode.contentRequired'))
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      description: form.description || null,
      content: form.content,
      is_active: form.is_active,
    }
    if (editingId.value) {
      await shortcodeApi.update(editingId.value, payload)
    } else {
      await shortcodeApi.create({...payload, code: form.code.trim()})
    }
    ElMessage.success(t('admin.common.save'))
    formVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(row: ShortcodeItem) {
  await ElMessageBox.confirm(
    t('admin.content.shortcode.deleteConfirm', {name: row.name || row.code}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await shortcodeApi.remove(row.id)
  ElMessage.success(t('admin.common.delete'))
  await load()
}

// ---- 复制代码 ----
function copyCode(code: string): void {
  navigator.clipboard
    ?.writeText(code)
    .then(() => ElMessage.success(t('admin.content.shortcode.copied')))
    .catch(() => ElMessage.warning(t('admin.content.shortcode.copyFailed')))
}
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <!-- 搜索区 -->
      <el-form :inline="true" :model="query" @submit.prevent="search()">
        <el-form-item :label="$t('admin.content.shortcode.keyword')">
          <el-input
            v-model="query.keyword"
            :placeholder="$t('admin.content.shortcode.keywordPlaceholder')"
            clearable
            style="width: 200px"
            @keyup.enter="search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="query.is_active" :placeholder="$t('admin.common.all')" clearable style="width: 110px">
            <el-option :label="$t('admin.common.enabled')" :value="true"/>
            <el-option :label="$t('admin.common.disabled')" :value="false"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="search()">{{ $t('admin.common.search') }}</el-button>
          <el-button :icon="Refresh" @click="reset()">{{ $t('admin.common.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <!-- 操作区 -->
      <div class="table-toolbar">
        <el-button v-auth="'module_content:shortcode:create'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.content.shortcode.createTitle') }}
        </el-button>
        <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: total}) }}</span>
      </div>

      <!-- 表格 -->
      <el-table v-loading="loading" :data="list" border stripe>
        <el-table-column :label="$t('admin.content.shortcode.code')" min-width="170" prop="code"
                         show-overflow-tooltip>
          <template #default="{ row }">
            <span class="shortcode-code">{{ (row as ShortcodeItem).code }}</span>
            <el-button :icon="CopyDocument" class="shortcode-copy" link size="small"
                       @click="copyCode((row as ShortcodeItem).code)"/>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.name')" min-width="140" prop="name" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.common.description')" min-width="160" prop="description"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.content.shortcode.content')" min-width="220" prop="content"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.common.status')" width="90">
          <template #default="{ row }">
            <el-tag :type="(row as ShortcodeItem).is_active ? 'success' : 'info'" size="small">
              {{ (row as ShortcodeItem).is_active ? $t('admin.common.enabled') : $t('admin.common.disabled') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="140">
          <template #default="{ row }">
            <el-button v-auth="'module_content:shortcode:edit'" link type="primary"
                       @click="openEdit(row as ShortcodeItem)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button v-auth="'module_content:shortcode:delete'" link type="danger"
                       @click="onDelete(row as ShortcodeItem)">
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
    <el-drawer v-model="formVisible" :title="formTitle" destroy-on-close size="460px">
      <el-form :model="form" label-width="90px">
        <el-form-item :label="$t('admin.content.shortcode.code')" required>
          <el-input v-model="form.code" :disabled="!!editingId"
                    :placeholder="$t('admin.content.shortcode.codePlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="form.name" :placeholder="$t('admin.content.shortcode.namePlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.shortcode.content')" required>
          <el-input
            v-model="form.content"
            :autosize="{minRows: 6, maxRows: 14}"
            :placeholder="$t('admin.content.shortcode.contentPlaceholder')"
            type="textarea"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="form.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.shortcode-code {
  margin-right: 4px;
  font-family: Menlo, Consolas, monospace;
  color: var(--el-color-primary);
}
</style>
