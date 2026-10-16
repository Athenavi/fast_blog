<script lang="ts" setup>
const {t} = useI18n()
/**
 * 自定义内容类型（列表 + 抽屉表单）
 *
 * 对齐 v3 `/content/custom-post-type`：类型定义管理；`slug` 创建后不可修改。
 */
import {Delete, Edit, Plus} from '@element-plus/icons-vue'
import {reactive, ref} from 'vue'

import {customPostTypeApi, type CustomPostTypeItem, type CustomPostTypePayload} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage} from '@/utils/feedback'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.customPostType.title',
  permission: 'module_content:custom_post_type:view',
})

const list = useAdminList<CustomPostTypeItem, PageQuery>({
  fetcher: (params) => customPostTypeApi.list(params),
  defaultQuery: {keyword: ''},
  syncUrl: true,
})

// ---------------------------------------------------------------- 抽屉表单
const drawerVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)

function emptyForm(): CustomPostTypePayload {
  return {
    name: '',
    slug: '',
    description: '',
    supports: '',
    has_archive: false,
    menu_icon: '',
    menu_position: 0,
    is_active: true,
  }
}

const form = reactive<CustomPostTypePayload>(emptyForm())

const formRules = computed(() => ({
  name: [{required: true, message: t('admin.content.customPostType.nameRequired'), trigger: 'blur'}],
  slug: [{required: true, message: t('admin.content.customPostType.slugRequired'), trigger: 'blur'}],
}))

function openCreate(): void {
  editingId.value = null
  Object.assign(form, emptyForm())
  drawerVisible.value = true
}

function openEdit(item: CustomPostTypeItem): void {
  editingId.value = item.id
  Object.assign(form, {
    name: item.name ?? '',
    slug: item.slug ?? '',
    description: item.description ?? '',
    supports: item.supports ?? '',
    has_archive: item.has_archive ?? false,
    menu_icon: item.menu_icon ?? '',
    menu_position: item.menu_position ?? 0,
    is_active: item.is_active ?? true,
  })
  drawerVisible.value = true
}

async function submitForm(): Promise<void> {
  const payload: CustomPostTypePayload = {
    name: (form.name ?? '').trim(),
    description: form.description || null,
    supports: form.supports || null,
    has_archive: form.has_archive,
    menu_icon: form.menu_icon || null,
    menu_position: form.menu_position,
    is_active: form.is_active,
  }

  saving.value = true
  try {
    if (editingId.value) {
      // slug 创建后不可改，更新负载不含 slug
      await customPostTypeApi.update(editingId.value, payload)
      ElMessage.success(t('admin.content.customPostType.saved'))
    } else {
      await customPostTypeApi.create({...payload, slug: (form.slug ?? '').trim()})
      ElMessage.success(t('admin.content.customPostType.created'))
    }
    drawerVisible.value = false
    await list.reload()
  } finally {
    saving.value = false
  }
}

async function removeRow(item: CustomPostTypeItem): Promise<void> {
  await list.remove(
    () => customPostTypeApi.remove(item.id),
    t('admin.content.customPostType.deleteConfirm', {name: item.name ?? item.slug ?? item.id}),
    t('admin.common.notice'),
    t('admin.content.customPostType.deleted'),
  )
}
</script>

<template>
  <AdminPage :desc="$t('admin.content.customPostType.desc')" :title="$t('admin.content.customPostType.title')">
    <template #actions>
      <el-button v-auth="'module_content:custom_post_type:create'" :icon="Plus" type="primary" @click="openCreate">
        {{ $t('admin.content.customPostType.createTitle') }}
      </el-button>
    </template>

    <AdminListShell
      :empty-desc="list.hasFilters.value ? $t('admin.content.customPostType.emptyFiltered') : $t('admin.content.customPostType.emptyDesc')"
      :empty-title="list.hasFilters.value ? $t('admin.content.customPostType.emptyFiltered') : $t('admin.content.customPostType.emptyTitle')"
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
        <el-form-item :label="$t('admin.content.customPostType.keyword')">
          <el-input v-model="list.query.keyword" :placeholder="$t('admin.content.customPostType.keywordPlaceholder')"
                    clearable
                    style="width: 200px" @keyup.enter="list.search()"/>
        </el-form-item>
      </template>

      <template #empty-actions>
        <el-button v-auth="'module_content:custom_post_type:create'" :icon="Plus" type="primary"
                   @click="openCreate">
          {{ $t('admin.content.customPostType.createTitle') }}
        </el-button>
      </template>

      <el-table-column :label="$t('admin.common.name')" min-width="200">
        <template #default="{row}">
          <div class="admin-cell-title">{{ row.name }}</div>
          <div class="admin-cell-sub">{{ row.slug || '-' }}</div>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.common.description')" min-width="200" show-overflow-tooltip>
        <template #default="{row}">{{ row.description || '-' }}</template>
      </el-table-column>

      <el-table-column :label="$t('admin.content.customPostType.supports')" min-width="180">
        <template #default="{row}">
          <span class="cpt-supports">{{ row.supports || '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.content.customPostType.hasArchive')" width="110">
        <template #default="{row}">
          <el-tag :type="row.has_archive ? 'success' : 'info'" size="small">
            {{ row.has_archive ? $t('admin.common.yes') : $t('admin.common.no') }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.content.customPostType.menuPosition')" prop="menu_position" width="110"/>

      <el-table-column :label="$t('admin.common.status')" width="100">
        <template #default="{row}">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{
              row.is_active
                ? $t('admin.content.customPostType.activeLabel')
                : $t('admin.content.customPostType.inactiveLabel')
            }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.common.updatedAt')" width="170">
        <template #default="{row}">{{ formatDateTime(row.updated_at) }}</template>
      </el-table-column>

      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="170">
        <template #default="{row}">
          <el-button v-auth="'module_content:custom_post_type:edit'" :icon="Edit" link type="primary"
                     @click="openEdit(row as CustomPostTypeItem)">
            {{ $t('admin.common.edit') }}
          </el-button>
          <el-button v-auth="'module_content:custom_post_type:delete'" :icon="Delete" link type="danger"
                     @click="removeRow(row as CustomPostTypeItem)">
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>

    <AdminFormDrawer
      v-model="drawerVisible"
      :loading="saving"
      :size="600"
      :title="editingId ? $t('admin.content.customPostType.editTitle') : $t('admin.content.customPostType.createTitle')"
      @confirm="submitForm"
    >
      <el-form :model="form" :rules="formRules" label-position="top">
        <el-form-item :label="$t('admin.common.name')" prop="name">
          <el-input v-model="form.name" maxlength="60" show-word-limit/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.customPostType.slug')" prop="slug">
          <el-input v-model="form.slug" :disabled="!!editingId"
                    :placeholder="$t('admin.content.customPostType.slugPlaceholder')"/>
          <div v-if="editingId" class="admin-cell-sub">
            {{ $t('admin.content.customPostType.slugLockedHint') }}
          </div>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description" :rows="2" maxlength="255" show-word-limit type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.customPostType.supports')">
          <el-input v-model="form.supports" :placeholder="$t('admin.content.customPostType.supportsHint')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.customPostType.hasArchive')">
          <el-switch v-model="form.has_archive"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.customPostType.menuIcon')">
          <el-input v-model="form.menu_icon" placeholder="Document"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.customPostType.menuPosition')">
          <el-input-number v-model="form.menu_position" :min="0"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.customPostType.activeLabel')">
          <el-switch v-model="form.is_active"/>
        </el-form-item>
      </el-form>
    </AdminFormDrawer>
  </AdminPage>
</template>

<style scoped>
.cpt-supports {
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  color: var(--admin-fg-muted);
}
</style>
