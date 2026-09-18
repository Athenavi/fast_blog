<script lang="ts" setup>
const {t} = useI18n()
/**
 * 分类管理（树形列表 + 增删改）
 *
 * 对齐 v3：`/content/category`，树数据来自 `tree`，
 * 字段见 `CategoryPayload`（name / slug / parent_id / sort_order / icon / color / is_visible）。
 */
import {Delete, Edit, Plus, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {reactive, ref} from 'vue'

import {categoryApi, type CategoryItem, type CategoryPayload} from '@/api'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'article.category',
  permission: 'module_content:category:view',
})

const loading = ref(false)
const tree = ref<CategoryItem[]>([])

async function loadTree(): Promise<void> {
  loading.value = true
  try {
    tree.value = await categoryApi.tree()
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------- 编辑
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)

function emptyForm(): CategoryPayload {
  return {
    name: '',
    slug: '',
    description: '',
    parent_id: null,
    sort_order: 0,
    icon: '',
    color: '',
    is_visible: true,
  }
}

const form = reactive<CategoryPayload>(emptyForm())

/** 顶级分类选项：编辑时排除自身（后端会做深度校验，这里先避免明显误操作） */
const parentOptions = computed(() =>
  (tree.value ?? []).filter((item) => item.id !== editingId.value),
)

function openCreate(parent?: CategoryItem): void {
  editingId.value = null
  Object.assign(form, emptyForm(), parent ? {parent_id: parent.id} : {})
  dialogVisible.value = true
}

function openEdit(row: CategoryItem): void {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    slug: row.slug ?? '',
    description: row.description ?? '',
    parent_id: row.parent_id ?? null,
    sort_order: row.sort_order ?? 0,
    icon: row.icon ?? '',
    color: row.color ?? '',
    is_visible: row.is_visible ?? true,
  })
  dialogVisible.value = true
}

async function submitForm(): Promise<void> {
  const name = (form.name ?? '').trim()
  if (!name) {
    ElMessage.warning(t('admin.content.category.enterACategoryName'))
    return
  }

  saving.value = true
  try {
    const payload: CategoryPayload = {...form, name}
    if (editingId.value) {
      await categoryApi.update(editingId.value, payload)
      ElMessage.success(t('admin.content.category.saved'))
    } else {
      await categoryApi.create(payload)
      ElMessage.success(t('admin.content.category.created'))
    }
    dialogVisible.value = false
    await loadTree()
  } finally {
    saving.value = false
  }
}

async function removeRow(row: CategoryItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.content.category.deleteConfirm', {name: row.name}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await categoryApi.remove(row.id)
  ElMessage.success(t('admin.content.category.deleted'))
  await loadTree()
}

onMounted(loadTree)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="toolbar">
        <el-button v-auth="'module_content:category:create'" :icon="Plus" type="primary" @click="openCreate()">
          {{ $t('admin.content.category.newCategory') }}
        </el-button>
        <el-button :icon="Refresh" circle @click="loadTree"/>
      </div>

      <el-table
        v-loading="loading"
        :data="tree"
        :tree-props="{children: 'children'}"
        default-expand-all
        row-key="id"
      >
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column :label="$t('admin.common.name')" min-width="200" prop="name">
          <template #default="{row}">
            <span class="name-cell">{{ row.name }}</span>
            <el-tag v-if="row.color" :color="row.color" class="ml-1" effect="dark" size="small">&nbsp;</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.content.category.alias')" min-width="140" prop="slug"/>
        <el-table-column :label="$t('admin.common.description')" min-width="200" prop="description"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.widget.order')" prop="sort_order" width="80"/>
        <el-table-column :label="$t('admin.content.category.visible')" width="80">
          <template #default="{row}">
            <el-tag :type="row.is_visible ? 'success' : 'info'" size="small">
              {{ row.is_visible ? t('admin.common.yes') : t('admin.common.no') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.updatedAt')" width="170">
          <template #default="{row}">{{ formatDateTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="220">
          <template #default="{row}">
            <el-button v-auth="'module_content:category:create'" :icon="Plus" link type="primary"
                       @click="openCreate(row)">
              {{ $t('admin.content.category.subCategory') }}
            </el-button>
            <el-button v-auth="'module_content:category:edit'" :icon="Edit" link type="primary" @click="openEdit(row)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button v-auth="'module_content:category:delete'" :icon="Delete" link type="danger"
                       @click="removeRow(row)">
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? t('admin.content.category.editCategory') : t('admin.content.category.newCategory')"
      destroy-on-close
      width="560px"
    >
      <el-form :model="form" label-width="90px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="form.name" maxlength="100" show-word-limit/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.category.parent')">
          <el-select v-model="form.parent_id" :placeholder="$t('admin.content.category.topLevelCategory')" clearable
                     style="width: 100%">
            <el-option v-for="item in parentOptions" :key="item.id" :label="item.name" :value="item.id"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.content.category.alias')">
          <el-input v-model="form.slug" :placeholder="$t('admin.content.category.urlAliasLeaveBlankToGenerate')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description" :rows="2" maxlength="255" show-word-limit type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.widget.order')">
          <el-input-number v-model="form.sort_order" :min="0"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.category.icon')">
          <el-input v-model="form.icon" :placeholder="$t('admin.content.category.iconNameOrUrl')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.category.color')">
          <el-input v-model="form.color" :placeholder="$t('admin.content.category.eG3B82F6')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.category.visible')">
          <el-switch v-model="form.is_visible"/>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.name-cell {
  font-weight: 500;
}

.ml-1 {
  margin-left: 4px;
}
</style>
