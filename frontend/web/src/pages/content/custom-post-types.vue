<script lang="ts" setup>
/**
 * 自定义内容类型（T5-11 批次 1）
 *
 * 对齐 v3 `/content/custom-post-type`：类型定义管理（slug 创建后不可改）。
 */
import {Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {customPostTypeApi, type CustomPostTypeItem} from '@/api'
import {useTable} from '@/hooks/useTable'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.customPostType.title',
  permission: 'module_content:custom_post_type:view',
})

const {t} = useI18n()

const {
  list, loading, total, page, pageSize, query, search, reset, load,
  onPageChange, onSizeChange,
} = useTable<CustomPostTypeItem>({fetcher: (params) => customPostTypeApi.list(params)})

const formVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({
  name: '', slug: '', description: '', supports: '',
  has_archive: false, menu_icon: '', menu_position: 0, is_active: true,
})

const formTitle = computed(() =>
  editingId.value ? t('admin.content.customPostType.editTitle') : t('admin.content.customPostType.createTitle'))

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    name: '', slug: '', description: '', supports: '',
    has_archive: false, menu_icon: '', menu_position: 0, is_active: true,
  })
  formVisible.value = true
}

function openEdit(row: CustomPostTypeItem) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name || '',
    slug: row.slug || '',
    description: row.description || '',
    supports: row.supports || '',
    has_archive: row.has_archive,
    menu_icon: row.menu_icon || '',
    menu_position: row.menu_position ?? 0,
    is_active: row.is_active,
  })
  formVisible.value = true
}

async function submitForm() {
  if (!form.name.trim() || !form.slug.trim()) {
    ElMessage.warning(t('admin.content.customPostType.nameRequired'))
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await customPostTypeApi.update(editingId.value, {
        name: form.name.trim(),
        description: form.description || null,
        supports: form.supports || null,
        has_archive: form.has_archive,
        menu_icon: form.menu_icon || null,
        menu_position: form.menu_position,
        is_active: form.is_active,
      })
    } else {
      await customPostTypeApi.create({
        name: form.name.trim(),
        slug: form.slug.trim(),
        description: form.description || null,
        supports: form.supports || null,
        has_archive: form.has_archive,
        menu_icon: form.menu_icon || null,
        menu_position: form.menu_position,
        is_active: form.is_active,
      })
    }
    ElMessage.success(t('admin.common.save'))
    formVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(row: CustomPostTypeItem) {
  await ElMessageBox.confirm(t('admin.content.customPostType.deleteConfirm'), t('admin.common.notice'), {type: 'warning'})
  await customPostTypeApi.remove(row.id)
  ElMessage.success(t('admin.common.delete'))
  await load()
}
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-form :inline="true" @submit.prevent="search()">
        <el-form-item :label="$t('admin.system.sensitiveWord.keyword')">
          <el-input v-model="query.keyword" clearable style="width: 180px" @keyup.enter="search()"/>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="search()">{{ $t('admin.common.search') }}</el-button>
          <el-button :icon="Refresh" @click="reset()">{{ $t('admin.common.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <div class="table-toolbar">
        <el-button v-auth="'module_content:custom_post_type:create'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.content.customPostType.createTitle') }}
        </el-button>
        <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: total}) }}</span>
      </div>

      <el-table v-loading="loading" :data="list" border stripe>
        <el-table-column :label="$t('admin.common.name')" min-width="140" prop="name"/>
        <el-table-column label="Slug" prop="slug" width="140"/>
        <el-table-column :label="$t('admin.common.description')" min-width="180" prop="description"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.content.customPostType.supports')" min-width="150" prop="supports"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.content.customPostType.hasArchive')" width="100">
          <template #default="{ row }">
            {{ (row as CustomPostTypeItem).has_archive ? $t('admin.common.yes') : $t('admin.common.no') }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.status')" width="90">
          <template #default="{ row }">
            <el-tag :type="(row as CustomPostTypeItem).is_active ? 'success' : 'info'" size="small">
              {{
                (row as CustomPostTypeItem).is_active ? $t('admin.system.sensitiveWord.active') : $t('admin.system.sensitiveWord.inactive')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
          <template #default="{ row }">
            <el-button v-auth="'module_content:custom_post_type:edit'" link type="primary"
                       @click="openEdit(row as CustomPostTypeItem)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button v-auth="'module_content:custom_post_type:delete'" link type="danger"
                       @click="onDelete(row as CustomPostTypeItem)">
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        :current-page="page" :page-size="pageSize" :total="total"
        background class="table-pagination" layout="total, sizes, prev, pager, next"
        @current-change="onPageChange" @size-change="onSizeChange"
      />
    </el-card>

    <el-drawer v-model="formVisible" :title="formTitle" destroy-on-close size="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="form.name"/>
        </el-form-item>
        <el-form-item label="Slug" required>
          <el-input v-model="form.slug" :disabled="!!editingId"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.customPostType.supports')">
          <el-input v-model="form.supports" :placeholder="$t('admin.content.customPostType.supportsHint')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.customPostType.hasArchive')">
          <el-switch v-model="form.has_archive"/>
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
