<script lang="ts" setup>
/**
 * 敏感词库管理（T5-11 样板域）
 *
 * 对齐 v3 `/system/sensitive-word`（复用共享反垃圾服务，写操作即时生效）。
 * 页面骨架与 role/user 页一致：搜索区 + 表格 + 抽屉表单 + 批量导入弹窗。
 */
import {Plus, Refresh, Search, Upload} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {sensitiveWordApi, type SensitiveWordItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useTable} from '@/hooks/useTable'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.sensitiveWord.title',
  permission: 'module_system:sensitive_word:view',
})

const {t} = useI18n()

interface SensitiveWordQueryForm extends PageQuery {
  keyword?: string
  level?: number
  is_active?: boolean
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
} = useTable<SensitiveWordItem, SensitiveWordQueryForm>({
  fetcher: (params) => sensitiveWordApi.list(params),
  defaultQuery: {keyword: '', level: undefined, is_active: undefined},
  syncUrl: true,
})

// ---- 新建 / 编辑 ----
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive<{
  word: string;
  level: number;
  action: string;
  replacement: string;
  category: string;
  is_active: boolean
}>({
  word: '',
  level: 1,
  action: 'block',
  replacement: '',
  category: '',
  is_active: true,
})

const formTitle = computed(() => (editingId.value ? t('admin.system.sensitiveWord.editTitle') : t('admin.system.sensitiveWord.createTitle')))

function openCreate() {
  editingId.value = null
  Object.assign(form, {word: '', level: 1, action: 'block', replacement: '', category: '', is_active: true})
  formVisible.value = true
}

function openEdit(row: SensitiveWordItem) {
  editingId.value = row.id
  Object.assign(form, {
    word: row.word,
    level: row.level,
    action: row.action,
    replacement: row.replacement || '',
    category: row.category || '',
    is_active: row.is_active,
  })
  formVisible.value = true
}

async function submitForm() {
  if (!form.word.trim()) {
    ElMessage.warning(t('admin.system.sensitiveWord.wordRequired'))
    return
  }
  saving.value = true
  try {
    const payload = {
      word: form.word.trim(),
      level: form.level,
      action: form.action,
      replacement: form.replacement || null,
      category: form.category || null,
      is_active: form.is_active,
    }
    if (editingId.value) {
      await sensitiveWordApi.update(editingId.value, payload)
    } else {
      await sensitiveWordApi.create(payload)
    }
    ElMessage.success(t('admin.common.save'))
    formVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(row: SensitiveWordItem) {
  await ElMessageBox.confirm(t('admin.system.sensitiveWord.deleteConfirm'), t('admin.common.notice'), {type: 'warning'})
  await sensitiveWordApi.remove(row.id)
  ElMessage.success(t('admin.common.delete'))
  await load()
}

async function toggleActive(row: SensitiveWordItem) {
  await sensitiveWordApi.update(row.id, {is_active: !row.is_active})
  await load()
}

// ---- 批量导入 ----
const importVisible = ref(false)
const importing = ref(false)
const importText = ref('')
const importLevel = ref(1)
const importAction = ref('block')

function openImport() {
  importText.value = ''
  importVisible.value = true
}

async function submitImport() {
  const words = importText.value.split(/\r?\n|[,，、]/).map(w => w.trim()).filter(Boolean)
  if (!words.length) {
    ElMessage.warning(t('admin.system.sensitiveWord.importEmpty'))
    return
  }
  importing.value = true
  try {
    const result = await sensitiveWordApi.batchImport(words, {level: importLevel.value, action: importAction.value})
    ElMessage.success(t('admin.system.sensitiveWord.importResult', {
      total: result.total ?? words.length,
      added: result.added ?? 0,
      duplicated: result.duplicated ?? 0,
    }))
    importVisible.value = false
    await load()
  } finally {
    importing.value = false
  }
}

function levelTag(level: number): string {
  return level >= 3 ? 'danger' : level === 2 ? 'warning' : 'info'
}
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <!-- 搜索区 -->
      <el-form :inline="true" :model="query" @submit.prevent="search()">
        <el-form-item :label="$t('admin.system.sensitiveWord.keyword')">
          <el-input
            v-model="query.keyword"
            :placeholder="$t('admin.system.sensitiveWord.keywordPlaceholder')"
            clearable
            style="width: 200px"
            @keyup.enter="search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.system.sensitiveWord.level')">
          <el-select v-model="query.level" :placeholder="$t('admin.common.all')" clearable style="width: 110px">
            <el-option :label="$t('admin.system.sensitiveWord.levelLow')" :value="1"/>
            <el-option :label="$t('admin.system.sensitiveWord.levelMid')" :value="2"/>
            <el-option :label="$t('admin.system.sensitiveWord.levelHigh')" :value="3"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="query.is_active" :placeholder="$t('admin.common.all')" clearable style="width: 110px">
            <el-option :label="$t('admin.system.sensitiveWord.active')" :value="true"/>
            <el-option :label="$t('admin.system.sensitiveWord.inactive')" :value="false"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="search()">{{ $t('admin.common.search') }}</el-button>
          <el-button :icon="Refresh" @click="reset()">{{ $t('admin.common.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <!-- 操作区 -->
      <div class="table-toolbar">
        <el-button v-auth="'module_system:sensitive_word:create'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.system.sensitiveWord.createTitle') }}
        </el-button>
        <el-button v-auth="'module_system:sensitive_word:create'" :icon="Upload" @click="openImport">
          {{ $t('admin.system.sensitiveWord.importTitle') }}
        </el-button>
        <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: total}) }}</span>
      </div>

      <!-- 表格 -->
      <AdminTableSkeleton v-if="loading && !list.length" :rows="5"/>

      <AdminEmpty v-else-if="!loading && !list.length" :title="$t('admin.common.empty')"/>
      <el-table v-else v-loading="loading" :data="list" border stripe>
        <el-table-column :label="$t('admin.system.sensitiveWord.word')" min-width="160" prop="word"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.sensitiveWord.level')" width="90">
          <template #default="{ row }">
            <el-tag :type="levelTag(row.level)" size="small">
              {{
                row.level === 3 ? $t('admin.system.sensitiveWord.levelHigh') : row.level === 2 ? $t('admin.system.sensitiveWord.levelMid') : $t('admin.system.sensitiveWord.levelLow')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.sensitiveWord.action')" width="100">
          <template #default="{ row }">
            {{
              row.action === 'block' ? $t('admin.system.sensitiveWord.actionBlock') : row.action === 'replace' ? $t('admin.system.sensitiveWord.actionReplace') : $t('admin.system.sensitiveWord.actionWarn')
            }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.sensitiveWord.replacement')" min-width="120" prop="replacement"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.sensitiveWord.category')" min-width="100" prop="category"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.common.status')" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? $t('admin.system.sensitiveWord.active') : $t('admin.system.sensitiveWord.inactive') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="220">
          <template #default="{ row }">
            <el-button v-auth="'module_system:sensitive_word:edit'" link type="primary"
                       @click="openEdit(row as SensitiveWordItem)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button
              v-auth="'module_system:sensitive_word:edit'"
              :type="row.is_active ? 'warning' : 'success'"
              link
              @click="toggleActive(row as SensitiveWordItem)"
            >
              {{ row.is_active ? $t('admin.system.sensitiveWord.inactive') : $t('admin.system.sensitiveWord.active') }}
            </el-button>
            <el-button v-auth="'module_system:sensitive_word:delete'" link type="danger"
                       @click="onDelete(row as SensitiveWordItem)">
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
        <el-form-item :label="$t('admin.system.sensitiveWord.word')" required>
          <el-input v-model="form.word" :placeholder="$t('admin.system.sensitiveWord.wordPlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.sensitiveWord.level')">
          <el-select v-model="form.level" style="width: 100%">
            <el-option :label="$t('admin.system.sensitiveWord.levelLow')" :value="1"/>
            <el-option :label="$t('admin.system.sensitiveWord.levelMid')" :value="2"/>
            <el-option :label="$t('admin.system.sensitiveWord.levelHigh')" :value="3"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.system.sensitiveWord.action')">
          <el-select v-model="form.action" style="width: 100%">
            <el-option :label="$t('admin.system.sensitiveWord.actionBlock')" value="block"/>
            <el-option :label="$t('admin.system.sensitiveWord.actionReplace')" value="replace"/>
            <el-option :label="$t('admin.system.sensitiveWord.actionWarn')" value="warn"/>
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.action === 'replace'" :label="$t('admin.system.sensitiveWord.replacement')">
          <el-input v-model="form.replacement"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.sensitiveWord.category')">
          <el-input v-model="form.category"/>
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

    <!-- 批量导入 -->
    <el-dialog v-model="importVisible" :title="$t('admin.system.sensitiveWord.importTitle')" width="520px">
      <el-form label-width="90px">
        <el-form-item :label="$t('admin.system.sensitiveWord.level')">
          <el-select v-model="importLevel" style="width: 100%">
            <el-option :label="$t('admin.system.sensitiveWord.levelLow')" :value="1"/>
            <el-option :label="$t('admin.system.sensitiveWord.levelMid')" :value="2"/>
            <el-option :label="$t('admin.system.sensitiveWord.levelHigh')" :value="3"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.system.sensitiveWord.action')">
          <el-select v-model="importAction" style="width: 100%">
            <el-option :label="$t('admin.system.sensitiveWord.actionBlock')" value="block"/>
            <el-option :label="$t('admin.system.sensitiveWord.actionReplace')" value="replace"/>
            <el-option :label="$t('admin.system.sensitiveWord.actionWarn')" value="warn"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.system.sensitiveWord.importContent')">
          <el-input
            v-model="importText"
            :autosize="{minRows: 8, maxRows: 16}"
            :placeholder="$t('admin.system.sensitiveWord.importPlaceholder')"
            type="textarea"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="importing" type="primary" @click="submitImport">
          {{ $t('admin.system.sensitiveWord.importBtn') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
