<script lang="ts" setup>
const {t} = useI18n()
/**
 * 短代码管理（列表 + 抽屉表单）
 *
 * 对齐 v3 `/content/shortcode`：`code` 创建后锁定（更新负载不含 code，重复 409 由请求拦截器提示）。
 * 列表支持按 `is_active` 筛选，开关可就地切换启用状态。
 */
import {CopyDocument, Delete, Edit, Plus} from '@element-plus/icons-vue'
import {reactive, ref} from 'vue'

import {shortcodeApi, type ShortcodeItem, type ShortcodePayload, type ShortcodeQuery} from '@/api'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage} from '@/utils/feedback'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.shortcode.title',
  permission: 'module_content:shortcode:view',
})

const list = useAdminList<ShortcodeItem, ShortcodeQuery>({
  fetcher: (params) => shortcodeApi.list(params),
  defaultQuery: {keyword: '', is_active: undefined},
  syncUrl: true,
})

const ACTIVE_OPTIONS = computed(() => [
  {label: t('admin.content.shortcode.activeLabel'), value: true},
  {label: t('admin.content.shortcode.inactiveLabel'), value: false},
])

function usage(item: ShortcodeItem): string {
  return `[${item.code}]`
}

async function copyUsage(item: ShortcodeItem): Promise<void> {
  try {
    await navigator.clipboard.writeText(usage(item))
    ElMessage.success(t('admin.content.shortcode.copied'))
  } catch {
    ElMessage.warning(t('admin.content.shortcode.copyFailed'))
  }
}

async function toggleActive(item: ShortcodeItem, value: boolean): Promise<void> {
  await shortcodeApi.update(item.id, {is_active: value})
  ElMessage.success(t('admin.content.shortcode.saved'))
  await list.reload()
}

// ---------------------------------------------------------------- 抽屉表单
const drawerVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)

function emptyForm(): ShortcodePayload {
  return {code: '', name: '', description: '', content: '', is_active: true}
}

const form = reactive<ShortcodePayload>(emptyForm())

const formRules = computed(() => ({
  code: [{required: !editingId.value, message: t('admin.content.shortcode.codeRequired'), trigger: 'blur'}],
  name: [{required: true, message: t('admin.content.shortcode.nameRequired'), trigger: 'blur'}],
  content: [{required: true, message: t('admin.content.shortcode.contentRequired'), trigger: 'blur'}],
}))

function openCreate(): void {
  editingId.value = null
  Object.assign(form, emptyForm())
  drawerVisible.value = true
}

function openEdit(item: ShortcodeItem): void {
  editingId.value = item.id
  Object.assign(form, {
    code: item.code,
    name: item.name,
    description: item.description ?? '',
    content: item.content,
    is_active: item.is_active,
  })
  drawerVisible.value = true
}

async function submitForm(): Promise<void> {
  saving.value = true
  try {
    if (editingId.value) {
      // code 创建后锁定，更新时不提交
      await shortcodeApi.update(editingId.value, {
        name: form.name,
        description: form.description,
        content: form.content,
        is_active: form.is_active,
      })
      ElMessage.success(t('admin.content.shortcode.saved'))
    } else {
      await shortcodeApi.create({...form})
      ElMessage.success(t('admin.content.shortcode.created'))
    }
    drawerVisible.value = false
    await list.reload()
  } finally {
    saving.value = false
  }
}

async function removeRow(item: ShortcodeItem): Promise<void> {
  await list.remove(
    () => shortcodeApi.remove(item.id),
    t('admin.content.shortcode.deleteConfirm', {name: item.name}),
    t('admin.common.notice'),
    t('admin.content.shortcode.deleted'),
  )
}
</script>

<template>
  <AdminPage :desc="$t('admin.content.shortcode.desc')" :title="$t('admin.content.shortcode.title')">
    <template #actions>
      <el-button v-auth="'module_content:shortcode:create'" :icon="Plus" type="primary" @click="openCreate">
        {{ $t('admin.content.shortcode.createTitle') }}
      </el-button>
    </template>

    <AdminListShell
      :empty-desc="list.hasFilters.value ? $t('admin.content.shortcode.emptyFiltered') : $t('admin.content.shortcode.emptyDesc')"
      :empty-title="list.hasFilters.value ? $t('admin.content.shortcode.emptyFiltered') : $t('admin.content.shortcode.emptyTitle')"
      :failed="list.failed.value"
      :loading="list.loading.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      :rows="list.rows.value"
      :selectable="false"
      :total="list.total.value"
      @refresh="list.reload"
      @reset="list.reset"
      @search="list.search"
      @page-change="list.onPageChange"
      @size-change="list.onSizeChange"
    >
      <template #filters>
        <el-form-item :label="$t('admin.content.shortcode.keyword')">
          <el-input
            v-model="list.query.keyword"
            clearable
            :placeholder="$t('admin.content.shortcode.keywordPlaceholder')"
            style="width: 200px"
            @keyup.enter="list.search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="list.query.is_active" :placeholder="$t('admin.common.all')" clearable
                     style="width: 140px">
            <el-option v-for="item in ACTIVE_OPTIONS" :key="String(item.value)" :label="item.label"
                       :value="item.value"/>
          </el-select>
        </el-form-item>
      </template>

      <template #empty-actions>
        <el-button v-auth="'module_content:shortcode:create'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.content.shortcode.createTitle') }}
        </el-button>
      </template>

      <el-table-column :label="$t('admin.content.shortcode.code')" width="190">
        <template #default="{row}">
          <el-tag class="shortcode-code" size="small" type="info">{{ usage(row as ShortcodeItem) }}</el-tag>
          <el-button :icon="CopyDocument" :title="$t('admin.content.shortcode.copyUsage')" link size="small"
                     @click="copyUsage(row as ShortcodeItem)"/>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.common.name')" min-width="160">
        <template #default="{row}">
          <div class="admin-cell-title">{{ row.name }}</div>
          <div v-if="row.description" class="admin-cell-sub">{{ row.description }}</div>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.content.shortcode.content')" min-width="240">
        <template #default="{row}">
          <code class="shortcode-preview">{{ (row.content || '').slice(0, 80) }}</code>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.common.status')" width="100">
        <template #default="{row}">
          <el-switch
            v-auth="'module_content:shortcode:edit'"
            :model-value="row.is_active"
            size="small"
            @update:model-value="(value: string | number | boolean) => toggleActive(row as ShortcodeItem, Boolean(value))"
          />
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.common.updatedAt')" width="170">
        <template #default="{row}">{{ formatDateTime(row.updated_at) }}</template>
      </el-table-column>

      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="170">
        <template #default="{row}">
          <el-button v-auth="'module_content:shortcode:edit'" :icon="Edit" link type="primary"
                     @click="openEdit(row as ShortcodeItem)">
            {{ $t('admin.common.edit') }}
          </el-button>
          <el-button v-auth="'module_content:shortcode:delete'" :icon="Delete" link type="danger"
                     @click="removeRow(row as ShortcodeItem)">
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>

    <AdminFormDrawer
      v-model="drawerVisible"
      :loading="saving"
      :size="620"
      :title="editingId ? $t('admin.content.shortcode.editTitle') : $t('admin.content.shortcode.createTitle')"
      @confirm="submitForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-position="top">
        <el-form-item :label="$t('admin.content.shortcode.code')" prop="code">
          <el-input v-model="form.code" :disabled="!!editingId"
                    :placeholder="$t('admin.content.shortcode.codePlaceholder')"/>
          <div v-if="editingId" class="admin-cell-sub">{{ $t('admin.content.shortcode.codeLockedHint') }}</div>
        </el-form-item>
        <el-form-item :label="$t('admin.common.name')" prop="name">
          <el-input v-model="form.name" :placeholder="$t('admin.content.shortcode.namePlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description" :rows="2" maxlength="255" show-word-limit type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.shortcode.content')" prop="content">
          <el-input v-model="form.content" :placeholder="$t('admin.content.shortcode.contentPlaceholder')"
                    :rows="10" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.shortcode.activeLabel')">
          <el-switch v-model="form.is_active"/>
        </el-form-item>
      </el-form>
    </AdminFormDrawer>
  </AdminPage>
</template>

<style scoped>
.shortcode-code {
  font-family: var(--font-mono, monospace);
}

.shortcode-preview {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  color: var(--admin-fg-subtle);
}
</style>
