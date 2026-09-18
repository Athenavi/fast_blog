<script lang="ts" setup>
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
  title: '分类',
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
    ElMessage.warning('请填写分类名称')
    return
  }

  saving.value = true
  try {
    const payload: CategoryPayload = {...form, name}
    if (editingId.value) {
      await categoryApi.update(editingId.value, payload)
      ElMessage.success('已保存')
    } else {
      await categoryApi.create(payload)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    await loadTree()
  } finally {
    saving.value = false
  }
}

async function removeRow(row: CategoryItem): Promise<void> {
  await ElMessageBox.confirm(
    `确定删除分类「${row.name}」吗？其下文章将失去该分类归属。`,
    '提示',
    {type: 'warning'},
  )
  await categoryApi.remove(row.id)
  ElMessage.success('已删除')
  await loadTree()
}

onMounted(loadTree)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="toolbar">
        <el-button v-auth="'module_content:category:create'" :icon="Plus" type="primary" @click="openCreate()">
          新建分类
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
        <el-table-column label="名称" min-width="200" prop="name">
          <template #default="{row}">
            <span class="name-cell">{{ row.name }}</span>
            <el-tag v-if="row.color" :color="row.color" class="ml-1" effect="dark" size="small">&nbsp;</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="别名" min-width="140" prop="slug"/>
        <el-table-column label="描述" min-width="200" prop="description" show-overflow-tooltip/>
        <el-table-column label="排序" prop="sort_order" width="80"/>
        <el-table-column label="可见" width="80">
          <template #default="{row}">
            <el-tag :type="row.is_visible ? 'success' : 'info'" size="small">
              {{ row.is_visible ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="170">
          <template #default="{row}">{{ formatDateTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" width="220">
          <template #default="{row}">
            <el-button v-auth="'module_content:category:create'" :icon="Plus" link type="primary"
                       @click="openCreate(row)">
              子分类
            </el-button>
            <el-button v-auth="'module_content:category:edit'" :icon="Edit" link type="primary" @click="openEdit(row)">
              编辑
            </el-button>
            <el-button v-auth="'module_content:category:delete'" :icon="Delete" link type="danger"
                       @click="removeRow(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑分类' : '新建分类'"
      destroy-on-close
      width="560px"
    >
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" maxlength="100" show-word-limit/>
        </el-form-item>
        <el-form-item label="父级">
          <el-select v-model="form.parent_id" clearable placeholder="顶级分类" style="width: 100%">
            <el-option v-for="item in parentOptions" :key="item.id" :label="item.name" :value="item.id"/>
          </el-select>
        </el-form-item>
        <el-form-item label="别名">
          <el-input v-model="form.slug" placeholder="URL 别名（留空由后端生成）"/>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" :rows="2" maxlength="255" show-word-limit type="textarea"/>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0"/>
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" placeholder="图标名或 URL"/>
        </el-form-item>
        <el-form-item label="颜色">
          <el-input v-model="form.color" placeholder="如 #3b82f6"/>
        </el-form-item>
        <el-form-item label="可见">
          <el-switch v-model="form.is_visible"/>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">保存</el-button>
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
