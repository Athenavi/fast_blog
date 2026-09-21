<script lang="ts" setup>
const {t} = useI18n()
/**
 * 分类管理（树形 + 拖拽排序 + 内联编辑 + 合并）
 *
 * 对齐 v3：`/content/category`（列表/树/增删改）。后端**没有** reorder / merge 端点，因此：
 *  - 拖拽排序：同父级内重排后，只对 `sort_order` 变化的行逐条 `PUT /{id}`（真实写库）；
 *  - 合并：把源分类的子分类与其文章迁移到目标分类，再删除源分类，全程逐条真实调用并汇总失败项。
 */
import {Delete, Edit, FolderAdd, Rank, Refresh, Search, Switch} from '@element-plus/icons-vue'
import {computed, reactive, ref} from 'vue'

import {categoryApi, type CategoryItem, type CategoryPayload} from '@/api'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.category.categoryManagement',
  permission: 'module_content:category:view',
})

/** 扁平化后的树行（带层级与父级，便于缩进渲染与同层拖拽） */
interface FlatRow {
  node: CategoryItem
  depth: number
  parentId: number | null
}

const loading = ref(false)
const saving = ref(false)
const tree = ref<CategoryItem[]>([])
const keyword = ref('')

function flatten(
  nodes: CategoryItem[],
  depth = 0,
  parentId: number | null = null,
  out: FlatRow[] = [],
): FlatRow[] {
  for (const node of nodes) {
    out.push({node, depth, parentId})
    if (node.children?.length) flatten(node.children, depth + 1, node.id, out)
  }
  return out
}

const rows = computed(() => {
  const all = flatten(tree.value)
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return all
  // 关键词过滤：命中节点连同其祖先一起保留，避免树结构断裂
  const byId = new Map(all.map((row) => [row.node.id, row]))
  const keep = new Set<number>()
  for (const row of all) {
    const haystack = `${row.node.name ?? ''} ${row.node.slug ?? ''}`.toLowerCase()
    if (!haystack.includes(kw)) continue
    keep.add(row.node.id)
    let parentId = row.parentId
    while (parentId !== null) {
      keep.add(parentId)
      parentId = byId.get(parentId)?.parentId ?? null
    }
  }
  return all.filter((row) => keep.has(row.node.id))
})

const totalCount = computed(() => flatten(tree.value).length)

async function loadTree(): Promise<void> {
  loading.value = true
  try {
    tree.value = await categoryApi.tree()
  } finally {
    loading.value = false
  }
}

/** 同父级的兄弟节点（拖拽排序的范围） */
function siblingsOf(parentId: number | null): CategoryItem[] {
  if (parentId === null) return tree.value
  const stack = [...tree.value]
  while (stack.length) {
    const node = stack.shift() as CategoryItem
    if (node.id === parentId) return node.children ?? []
    if (node.children?.length) stack.push(...node.children)
  }
  return []
}

// ---------------------------------------------------------------- 拖拽排序
const draggingId = ref<number | null>(null)
const dropTargetId = ref<number | null>(null)

function onDragStart(row: FlatRow): void {
  draggingId.value = row.node.id
}

function onDragOver(row: FlatRow): void {
  if (draggingId.value !== null && draggingId.value !== row.node.id) dropTargetId.value = row.node.id
}

function resetDrag(): void {
  draggingId.value = null
  dropTargetId.value = null
}

async function onDrop(target: FlatRow): Promise<void> {
  const sourceId = draggingId.value
  resetDrag()
  if (sourceId === null || sourceId === target.node.id) return

  // 只在同一父级内排序；跨层级移动请用「编辑 → 上级分类」
  const siblings = siblingsOf(target.parentId)
  const from = siblings.findIndex((item) => item.id === sourceId)
  const to = siblings.findIndex((item) => item.id === target.node.id)
  if (from < 0 || to < 0 || from === to) return

  const reordered = [...siblings]
  const [moved] = reordered.splice(from, 1)
  if (!moved) return
  reordered.splice(to, 0, moved)

  const changed = reordered
    .map((item, index) => ({item, sortOrder: index}))
    .filter(({item, sortOrder}) => (item.sort_order ?? 0) !== sortOrder)
  if (!changed.length) return

  saving.value = true
  try {
    const results = await Promise.allSettled(
      changed.map(({item, sortOrder}) => categoryApi.update(item.id, {sort_order: sortOrder})),
    )
    const failed = results.filter((item) => item.status === 'rejected').length
    if (failed) ElMessage.warning(t('admin.content.category.batchPartialFailed', {n: failed}))
    else ElMessage.success(t('admin.content.category.sortSaved'))
    await loadTree()
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------- 内联编辑
const editingRowId = ref<number | null>(null)
const editingName = ref('')

function startInlineEdit(row: FlatRow): void {
  editingRowId.value = row.node.id
  editingName.value = row.node.name ?? ''
}

function cancelInlineEdit(): void {
  editingRowId.value = null
  editingName.value = ''
}

async function commitInlineEdit(row: FlatRow): Promise<void> {
  const name = editingName.value.trim()
  if (!name) {
    ElMessage.warning(t('admin.content.category.enterACategoryName'))
    return
  }
  if (name === row.node.name) {
    cancelInlineEdit()
    return
  }
  saving.value = true
  try {
    await categoryApi.update(row.node.id, {name})
    ElMessage.success(t('admin.content.category.saved'))
    cancelInlineEdit()
    await loadTree()
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------- 新建 / 编辑
const dialogVisible = ref(false)
const formEditingId = ref<number | null>(null)

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

const parentOptions = computed(() =>
  flatten(tree.value)
    .filter((row) => row.node.id !== formEditingId.value)
    .map((row) => ({id: row.node.id, label: `${'　'.repeat(row.depth)}${row.node.name ?? ''}`})),
)

function openCreate(parent?: CategoryItem): void {
  formEditingId.value = null
  Object.assign(form, emptyForm(), parent ? {parent_id: parent.id} : {})
  dialogVisible.value = true
}

function openEdit(row: FlatRow): void {
  formEditingId.value = row.node.id
  Object.assign(form, {
    name: row.node.name ?? '',
    slug: row.node.slug ?? '',
    description: row.node.description ?? '',
    parent_id: row.node.parent_id ?? null,
    sort_order: row.node.sort_order ?? 0,
    icon: row.node.icon ?? '',
    color: row.node.color ?? '',
    is_visible: row.node.is_visible ?? true,
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
    if (formEditingId.value) {
      await categoryApi.update(formEditingId.value, {...form, name})
      ElMessage.success(t('admin.content.category.saved'))
    } else {
      await categoryApi.create({...form, name})
      ElMessage.success(t('admin.content.category.created'))
    }
    dialogVisible.value = false
    await loadTree()
  } finally {
    saving.value = false
  }
}

async function toggleVisible(row: FlatRow): Promise<void> {
  await categoryApi.update(row.node.id, {is_visible: !row.node.is_visible})
  await loadTree()
}

async function removeRow(row: FlatRow): Promise<void> {
  const childCount = row.node.children?.length ?? 0
  await ElMessageBox.confirm(
    childCount
      ? t('admin.content.category.deleteWithChildrenConfirm', {name: row.node.name ?? '', n: childCount})
      : t('admin.content.category.deleteConfirm', {name: row.node.name ?? ''}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await categoryApi.remove(row.node.id)
  ElMessage.success(t('admin.content.category.deleted'))
  await loadTree()
}

// ---------------------------------------------------------------- 合并
const mergeVisible = ref(false)
const mergeSource = ref<FlatRow | null>(null)
const mergeTargetId = ref<number | null>(null)

const mergeOptions = computed(() =>
  flatten(tree.value)
    .filter((row) => row.node.id !== mergeSource.value?.node.id)
    .map((row) => ({id: row.node.id, label: `${'　'.repeat(row.depth)}${row.node.name ?? ''}`})),
)

function openMerge(row: FlatRow): void {
  mergeSource.value = row
  mergeTargetId.value = null
  mergeVisible.value = true
}

/** 合并 = 迁移子分类 → 迁移文章 → 删除源分类（逐条真实调用） */
async function submitMerge(): Promise<void> {
  const source = mergeSource.value
  const targetId = mergeTargetId.value
  if (!source || !targetId) {
    ElMessage.warning(t('admin.content.category.mergeTargetRequired'))
    return
  }

  const targetLabel =
    mergeOptions.value.find((item) => item.id === targetId)?.label.trim() ?? String(targetId)
  await ElMessageBox.confirm(
    t('admin.content.category.mergeConfirm', {source: source.node.name ?? '', target: targetLabel}),
    t('admin.common.notice'),
    {type: 'warning'},
  )

  saving.value = true
  try {
    const result = await categoryApi.merge(source.node.id, targetId)
    ElMessage.success(
      t('admin.content.category.mergeDone', {
        children: result.moved_children,
        articles: result.moved_articles,
      }),
    )
    mergeVisible.value = false
    await loadTree()
  } finally {
    saving.value = false
  }
}

onMounted(loadTree)
</script>

<template>
  <AdminPage :desc="$t('admin.content.category.desc')" :title="$t('admin.content.category.categoryManagement')">
    <template #actions>
      <el-button v-auth="'module_content:category:create'" :icon="FolderAdd" type="primary" @click="openCreate()">
        {{ $t('admin.content.category.newCategory') }}
      </el-button>
    </template>

    <div v-loading="loading" class="admin-card cat-panel">
      <div class="admin-toolbar">
        <el-input v-model="keyword" :placeholder="$t('admin.content.category.searchPlaceholder')" clearable
                  style="width: 220px">
          <template #prefix>
            <el-icon>
              <Search/>
            </el-icon>
          </template>
        </el-input>
        <el-button :icon="Refresh" :title="$t('admin.common.refresh')" circle @click="loadTree"/>
        <span class="admin-toolbar__spacer"/>
        <span class="admin-toolbar__total">{{ $t('admin.common.totalItems', {n: totalCount}) }}</span>
      </div>

      <p class="cat-hint">{{ $t('admin.content.category.dragHint') }}</p>

      <AdminTableSkeleton v-if="loading && !rows.length" :rows="5"/>

      <AdminEmpty v-else-if="!rows.length" :desc="$t('admin.content.category.emptyDesc')"
                  :title="$t('admin.content.category.emptyTitle')">
        <el-button v-auth="'module_content:category:create'" :icon="FolderAdd" type="primary" @click="openCreate()">
          {{ $t('admin.content.category.newCategory') }}
        </el-button>
      </AdminEmpty>

      <ul v-else class="cat-list">
        <li
          v-for="row in rows"
          :key="row.node.id"
          :class="{
            'cat-row--dragging': draggingId === row.node.id,
            'cat-row--drop': dropTargetId === row.node.id && draggingId !== row.node.id,
          }"
          :style="{paddingLeft: `${12 + row.depth * 22}px`}"
          class="cat-row"
          @dragover.prevent="onDragOver(row)"
          @drop.prevent="onDrop(row)"
        >
          <el-icon
            :title="$t('admin.content.category.dragHint')"
            class="cat-row__handle"
            draggable="true"
            @dragend="resetDrag"
            @dragstart="onDragStart(row)"
          >
            <Rank/>
          </el-icon>

          <span v-if="row.node.color" :style="{background: row.node.color}" class="cat-row__color"/>

          <template v-if="editingRowId === row.node.id">
            <el-input
              v-model="editingName"
              class="cat-row__inline"
              maxlength="60"
              size="small"
              @blur="commitInlineEdit(row)"
              @keyup.enter="commitInlineEdit(row)"
              @keyup.esc="cancelInlineEdit"
            />
          </template>
          <template v-else>
            <button class="cat-row__name" type="button" @click="startInlineEdit(row)">
              {{ row.node.name }}
            </button>
            <span class="cat-row__slug">{{ row.node.slug || '-' }}</span>
          </template>

          <el-tag class="cat-row__count" size="small" type="info">
            {{ $t('admin.content.category.articleCount', {n: row.node.articles_count ?? 0}) }}
          </el-tag>

          <el-switch v-model="row.node.is_visible" :disabled="saving" size="small" @change="toggleVisible(row)"/>
          <span class="cat-row__vis">{{ $t('admin.content.category.visible') }}</span>

          <span class="cat-row__ops">
            <el-button v-auth="'module_content:category:create'" :icon="FolderAdd" :title="$t('admin.content.category.subCategory')" link
                       size="small" @click="openCreate(row.node)"/>
            <el-button v-auth="'module_content:category:edit'" :icon="Edit" :title="$t('admin.common.edit')" link
                       size="small" @click="openEdit(row)"/>
            <el-button v-auth="'module_content:category:edit'" :icon="Switch" :title="$t('admin.content.category.merge')" link
                       size="small" @click="openMerge(row)"/>
            <el-button v-auth="'module_content:category:delete'" :icon="Delete" :title="$t('admin.common.delete')" link size="small"
                       type="danger" @click="removeRow(row)"/>
          </span>
        </li>
      </ul>
    </div>

    <!-- 新建 / 编辑 -->
    <el-dialog
      v-model="dialogVisible"
      :title="formEditingId ? $t('admin.content.category.editCategory') : $t('admin.content.category.newCategory')"
      width="560px"
    >
      <el-form :model="form" label-position="top">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="form.name" maxlength="60" show-word-limit/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.category.parent')">
          <el-select v-model="form.parent_id" :placeholder="$t('admin.content.category.topLevelCategory')" clearable
                     style="width: 100%">
            <el-option v-for="item in parentOptions" :key="item.id" :label="item.label" :value="item.id"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.content.category.alias')">
          <el-input v-model="form.slug" :placeholder="$t('admin.content.category.urlAliasLeaveBlankToGenerate')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description" :rows="2" maxlength="255" show-word-limit type="textarea"/>
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

    <!-- 合并 -->
    <el-dialog v-model="mergeVisible" :title="$t('admin.content.category.merge')" width="520px">
      <el-alert :closable="false" :title="$t('admin.content.category.mergeHint')" class="merge-alert" show-icon
                type="warning"/>
      <el-form label-position="top">
        <el-form-item :label="$t('admin.content.category.mergeSource')">
          <el-input :model-value="mergeSource?.node.name ?? ''" disabled/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.category.mergeTarget')" required>
          <el-select v-model="mergeTargetId" :placeholder="$t('admin.content.category.pleaseSelect')" filterable
                     style="width: 100%">
            <el-option v-for="item in mergeOptions" :key="item.id" :label="item.label" :value="item.id"/>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="mergeVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="danger" @click="submitMerge">
          {{ $t('admin.content.category.merge') }}
        </el-button>
      </template>
    </el-dialog>
  </AdminPage>
</template>

<style scoped>
.cat-panel {
  padding: var(--admin-gap-lg);
}

.cat-hint {
  margin: 0 0 var(--admin-gap-sm);
  font-size: 12.5px;
  color: var(--admin-fg-subtle);
}

.cat-list {
  margin: 0;
  padding: 0;
  list-style: none;
  border: 1px solid var(--admin-line);
  border-radius: var(--admin-radius);
  overflow: hidden;
}

.cat-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--admin-line);
  background: var(--admin-surface);
  transition: background-color 0.15s ease;
}

.cat-row:last-child {
  border-bottom: none;
}

.cat-row:hover {
  background: var(--admin-surface-hover);
}

.cat-row--dragging {
  opacity: 0.5;
}

.cat-row--drop {
  box-shadow: inset 0 2px 0 var(--admin-primary);
}

.cat-row__handle {
  cursor: grab;
  color: var(--admin-fg-subtle);
}

.cat-row__color {
  flex: none;
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.cat-row__name {
  padding: 0;
  border: none;
  background: none;
  font: inherit;
  font-weight: 500;
  color: var(--admin-fg);
  cursor: text;
}

.cat-row__name:hover {
  color: var(--admin-primary);
}

.cat-row__inline {
  width: 220px;
}

.cat-row__slug {
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

.cat-row__count {
  margin-left: auto;
}

.cat-row__vis {
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

.cat-row__ops {
  display: flex;
  gap: 2px;
  margin-left: 8px;
}

.merge-alert {
  margin-bottom: var(--admin-gap);
}
</style>
