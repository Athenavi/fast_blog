<script lang="ts" setup>
const {t} = useI18n()
/**
 * 系统设置（键值对管理）
 *
 * 对齐 v3：`/system/setting` 列表、`PUT /system/setting/{key}` upsert、
 * `DELETE /system/setting/{key}` 删除。`is_public=true` 的项会随
 * `/system/setting/public` 下发给前台（站点名、描述、页脚等）。
 *
 * 设置项总量有限，接口不分页：列表壳关闭分页器。
 */
import {Delete, Edit, Plus} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {reactive, ref} from 'vue'

import {settingApi, type SettingItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.setting.title',
  permission: 'module_system:setting:view',
})

const TYPES = [
  {label: t('admin.system.setting.typeString'), value: 'string'},
  {label: t('admin.system.setting.typeNumber'), value: 'number'},
  {label: t('admin.system.setting.typeBoolean'), value: 'boolean'},
  {label: 'JSON', value: 'json'},
]

interface SettingQueryForm extends PageQuery {
  is_public?: boolean
}

const list = useAdminList<SettingItem, SettingQueryForm>({
  fetcher: (params) => settingApi.list(params),
  defaultQuery: {keyword: '', is_public: undefined},
  syncUrl: true,
})

const dialogVisible = ref(false)
const saving = ref(false)
/** null 表示新增 */
const editingKey = ref<string | null>(null)

const form = reactive({
  setting_key: '',
  setting_value: '',
  setting_type: 'string',
  description: '',
  is_public: false,
})

function openCreate(): void {
  editingKey.value = null
  Object.assign(form, {
    setting_key: '',
    setting_value: '',
    setting_type: 'string',
    description: '',
    is_public: false,
  })
  dialogVisible.value = true
}

function openEdit(row: SettingItem): void {
  editingKey.value = row.setting_key
  Object.assign(form, {
    setting_key: row.setting_key,
    setting_value: row.setting_value ?? '',
    setting_type: row.setting_type ?? 'string',
    description: row.description ?? '',
    is_public: row.is_public,
  })
  dialogVisible.value = true
}

async function submitForm(): Promise<void> {
  const key = form.setting_key.trim()
  if (!key) {
    ElMessage.warning(t('admin.system.setting.keyRequired'))
    return
  }
  if (!/^[\w.:-]+$/.test(key)) {
    ElMessage.warning(t('admin.system.setting.keyCharset'))
    return
  }

  saving.value = true
  try {
    await settingApi.save(key, {
      setting_key: key,
      setting_value: form.setting_value,
      setting_type: form.setting_type,
      description: form.description,
      is_public: form.is_public,
    })
    ElMessage.success(t('admin.system.setting.saved'))
    dialogVisible.value = false
    await list.reload()
  } finally {
    saving.value = false
  }
}

async function removeRow(row: SettingItem): Promise<void> {
  await ElMessageBox.confirm(t('admin.system.setting.confirmDelete', {key: row.setting_key}), t('admin.common.notice'), {type: 'warning'})
  await settingApi.remove(row.setting_key)
  ElMessage.success(t('admin.system.setting.deleted'))
  await list.reload()
}
</script>

<template>
  <AdminPage :desc="$t('admin.system.setting.desc')" :title="$t('admin.system.setting.title')">
    <template #actions>
      <el-button v-auth="'module_system:setting:edit'" :icon="Plus" type="primary" @click="openCreate">
        {{ $t('admin.system.setting.createTitle') }}
      </el-button>
    </template>

    <AdminListShell
      :empty-desc="list.hasFilters.value
        ? $t('admin.system.setting.emptyFiltered')
        : $t('admin.system.setting.emptyDesc')"
      :empty-title="$t('admin.system.setting.emptyTitle')"
      :failed="list.failed.value"
      :loading="list.loading.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      :paginate="false"
      :rows="list.rows.value"
      :selectable="false"
      :total="list.total.value"
      @refresh="list.reload"
      @reset="list.reset"
      @search="list.search"
    >
      <template #filters>
        <el-form-item :label="$t('admin.system.setting.keyword')">
          <el-input v-model="list.query.keyword" :placeholder="$t('admin.system.setting.keywordPlaceholder')"
                    clearable style="width: 220px"
                    @keyup.enter="list.search()"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.setting.publicLabel')">
          <el-select v-model="list.query.is_public" :placeholder="$t('admin.common.all')" clearable
                     style="width: 130px">
            <el-option :label="$t('admin.system.setting.publicLabel')" :value="true"/>
            <el-option :label="$t('admin.system.setting.adminOnly')" :value="false"/>
          </el-select>
        </el-form-item>
      </template>

      <el-table-column :label="$t('admin.system.setting.key')" min-width="220">
        <template #default="{row}">
          <code class="key">{{ row.setting_key }}</code>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.system.setting.value')" min-width="240">
        <template #default="{row}">
          <span class="setting-value">{{ row.setting_value ?? '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.system.setting.type')" prop="setting_type" width="90"/>
      <el-table-column :label="$t('admin.common.description')" min-width="180" prop="description"
                       show-overflow-tooltip/>
      <el-table-column :label="$t('admin.system.setting.publicLabel')" width="80">
        <template #default="{row}">
          <el-tag :type="row.is_public ? 'success' : 'info'" size="small">
            {{ row.is_public ? t('admin.common.yes') : t('admin.common.no') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.updatedAt')" width="170">
        <template #default="{row}">{{ formatDateTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
        <template #default="{row}">
          <el-button v-auth="'module_system:setting:edit'" :icon="Edit" link type="primary" @click="openEdit(row)">
            {{ $t('admin.common.edit') }}
          </el-button>
          <el-button v-auth="'module_system:setting:edit'" :icon="Delete" link type="danger" @click="removeRow(row)">
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>

    <el-dialog
      v-model="dialogVisible"
      :title="editingKey ? t('admin.system.setting.editTitle') : t('admin.system.setting.createTitle')"
      destroy-on-close
      width="560px"
    >
      <el-form :model="form" label-width="90px">
        <el-form-item :label="$t('admin.system.setting.key')" required>
          <el-input v-model="form.setting_key" :disabled="Boolean(editingKey)"
                    :placeholder="$t('admin.system.setting.keyPlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.setting.value')">
          <el-input v-model="form.setting_value" :placeholder="$t('admin.system.setting.valuePlaceholder')" :rows="3"
                    type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.setting.type')">
          <el-select v-model="form.setting_type" style="width: 100%">
            <el-option v-for="item in TYPES" :key="item.value" :label="item.label" :value="item.value"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description" maxlength="255" show-word-limit/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.setting.publicLabel')">
          <el-switch v-model="form.is_public"/>
          <span class="switch-hint">{{ $t('admin.system.setting.publicHint') }}</span>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>
  </AdminPage>
</template>

<style scoped>
.key {
  padding: 1px 6px;
  font-size: 13px;
  background: var(--color-surface-soft);
  border-radius: 4px;
}

.setting-value {
  color: var(--color-fg-muted);
  word-break: break-all;
}

.switch-hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--color-fg-subtle);
}
</style>
