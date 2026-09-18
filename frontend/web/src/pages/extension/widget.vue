<script lang="ts" setup>
/**
 * 小部件管理
 *
 * 对齐 v3 `/extension/widget`：按区域/类型筛选、创建/更新、启停、排序、删除。
 * 部件配置（`config`）是自由 JSON，这里用文本域编辑并做解析校验。
 */
import {Delete, Edit, Plus, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {reactive, ref} from 'vue'

import {widgetApi, type WidgetItem} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '小部件',
  permission: 'module_extension:widget:view',
})

const loading = ref(false)
const list = ref<WidgetItem[]>([])
const total = ref(0)
const types = ref<Array<Record<string, unknown>>>([])
const areas = ref<Array<Record<string, unknown>>>([])

const query = reactive({
  area: '' as string | undefined,
  widget_type: '' as string | undefined,
  is_active: undefined as boolean | undefined,
})

async function loadList(): Promise<void> {
  loading.value = true
  try {
    const data = await widgetApi.list({
      ...(query.area ? {area: query.area} : {}),
      ...(query.widget_type ? {widget_type: query.widget_type} : {}),
      ...(query.is_active === undefined ? {} : {is_active: query.is_active}),
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadMeta(): Promise<void> {
  const [t, a] = await Promise.all([
    widgetApi.types().catch(() => []),
    widgetApi.areas().catch(() => []),
  ])
  types.value = t
  areas.value = a
}

/** 后端返回的元信息字段名不完全统一，这里做兼容提取 */
function labelOf(item: Record<string, unknown>): string {
  const value = item.label ?? item.name ?? item.title ?? item.value ?? item.area ?? item.type ?? item.key
  return String(value ?? '')
}

function valueOf(item: Record<string, unknown>): string {
  const value = item.value ?? item.name ?? item.key ?? item.area ?? item.type ?? item.slug
  return String(value ?? '')
}

// ---------------------------------------------------------------- 编辑
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)

const form = reactive({
  widget_type: '',
  area: '',
  title: '',
  configText: '{}',
  order_index: 0,
  is_active: true,
})

function openCreate(): void {
  editingId.value = null
  Object.assign(form, {
    widget_type: valueOf(types.value[0] ?? {}) || 'html',
    area: valueOf(areas.value[0] ?? {}) || 'sidebar',
    title: '',
    configText: '{\n  \n}',
    order_index: 0,
    is_active: true,
  })
  dialogVisible.value = true
}

function openEdit(row: WidgetItem): void {
  editingId.value = row.id
  Object.assign(form, {
    widget_type: row.widget_type ?? '',
    area: row.area ?? '',
    title: row.title ?? '',
    configText: JSON.stringify(row.config ?? {}, null, 2),
    order_index: row.order_index ?? 0,
    is_active: row.is_active,
  })
  dialogVisible.value = true
}

async function submitForm(): Promise<void> {
  if (!form.widget_type || !form.area) {
    ElMessage.warning('请选择部件类型与所属区域')
    return
  }

  let config: Record<string, unknown> = {}
  try {
    const parsed = form.configText.trim() ? JSON.parse(form.configText) : {}
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('必须是 JSON 对象')
    }
    config = parsed as Record<string, unknown>
  } catch (error) {
    ElMessage.warning(`配置不是合法的 JSON 对象：${(error as Error).message}`)
    return
  }

  saving.value = true
  try {
    const payload = {
      widget_type: form.widget_type,
      area: form.area,
      title: form.title,
      config,
      order_index: form.order_index,
      is_active: form.is_active,
    }
    if (editingId.value) {
      await widgetApi.update(editingId.value, payload)
      ElMessage.success('已保存')
    } else {
      await widgetApi.create(payload)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    await loadList()
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------- 行内操作
async function toggle(row: WidgetItem): Promise<void> {
  const next = !row.is_active
  await widgetApi.toggle(row.id, next)
  row.is_active = next
  ElMessage.success(next ? '已启用' : '已停用')
}

async function move(row: WidgetItem, delta: number): Promise<void> {
  const next = (row.order_index ?? 0) + delta
  if (next < 0) return
  await widgetApi.reorder([{id: row.id, order_index: next}])
  await loadList()
}

async function removeRow(row: WidgetItem): Promise<void> {
  await ElMessageBox.confirm(`确定删除小部件「${row.title || row.widget_type}」吗？`, '提示', {type: 'warning'})
  await widgetApi.remove(row.id)
  ElMessage.success('已删除')
  await loadList()
}

onMounted(async () => {
  await Promise.all([loadMeta(), loadList()])
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="区域">
          <el-select v-model="query.area" clearable placeholder="全部" style="width: 150px">
            <el-option v-for="item in areas" :key="valueOf(item)" :label="labelOf(item)" :value="valueOf(item)"/>
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="query.widget_type" clearable placeholder="全部" style="width: 150px">
            <el-option v-for="item in types" :key="valueOf(item)" :label="labelOf(item)" :value="valueOf(item)"/>
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.is_active" clearable placeholder="全部" style="width: 120px">
            <el-option :value="true" label="已启用"/>
            <el-option :value="false" label="已停用"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Refresh" type="primary" @click="loadList">查询</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar">
        <el-button v-auth="'module_extension:widget:edit'" :icon="Plus" type="primary" @click="openCreate">
          新建小部件
        </el-button>
        <el-button :icon="Refresh" circle class="ml-auto" @click="loadList"/>
      </div>

      <el-table v-loading="loading" :data="list" row-key="id">
        <el-table-column label="排序" prop="order_index" width="90">
          <template #default="{row}">
            <el-button :disabled="row.order_index <= 0" link @click="move(row, -1)">↑</el-button>
            <el-button link @click="move(row, 1)">↓</el-button>
          </template>
        </el-table-column>
        <el-table-column label="标题" min-width="180">
          <template #default="{row}">{{ row.title || `（未命名 ${row.widget_type}）` }}</template>
        </el-table-column>
        <el-table-column label="类型" prop="widget_type" width="140"/>
        <el-table-column label="区域" prop="area" width="140"/>
        <el-table-column label="状态" width="100">
          <template #default="{row}">
            <el-switch
              :disabled="false"
              :model-value="row.is_active"
              @change="toggle(row)"
            />
          </template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" width="150">
          <template #default="{row}">
            <el-button
              v-auth="'module_extension:widget:edit'"
              :icon="Edit"
              link
              type="primary"
              @click="openEdit(row)"
            >
              编辑
            </el-button>
            <el-button
              v-auth="'module_extension:widget:edit'"
              :icon="Delete"
              link
              type="danger"
              @click="removeRow(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <p class="hint">共 {{ total }} 个小部件</p>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑小部件' : '新建小部件'"
      destroy-on-close
      width="640px"
    >
      <el-form :model="form" label-width="90px">
        <el-form-item label="类型" required>
          <el-select v-model="form.widget_type" allow-create filterable style="width: 100%">
            <el-option v-for="item in types" :key="valueOf(item)" :label="labelOf(item)" :value="valueOf(item)"/>
          </el-select>
        </el-form-item>
        <el-form-item label="区域" required>
          <el-select v-model="form.area" allow-create filterable style="width: 100%">
            <el-option v-for="item in areas" :key="valueOf(item)" :label="labelOf(item)" :value="valueOf(item)"/>
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="form.title" maxlength="120" show-word-limit/>
        </el-form-item>
        <el-form-item label="配置">
          <el-input v-model="form.configText" :rows="8" placeholder="JSON 对象，如 {&quot;limit&quot;: 5}"
                    type="textarea"/>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.order_index" :min="0"/>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active"/>
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
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.ml-auto {
  margin-left: auto;
}

.hint {
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
