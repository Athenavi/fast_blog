<script lang="ts" setup>
/**
 * 后台菜单与角色菜单授权（/system/admin-menus，system 域）
 *
 * 对齐后端 `src/api/v3/modules/system/admin_menu`：
 *   - 左侧：菜单树（`/tree`），点击节点载入右侧表单；
 *   - 右侧：菜单信息表单（新建 / 编辑 / 删除，走 POST/PUT/DELETE）；
 *   - 底部：角色菜单授权（选择角色 → 读 `/role/{role_id}` → 勾选树 → PUT 全量覆盖）；
 *   - 顶部：当前用户可见菜单标识（`/my`）与菜单总数（`/list` 分页信封的 total）。
 *
 * 本页面是**后台管理菜单（admin_menus）**，与既有 `src/pages/system/menu.vue`
 * （前台导航菜单 + 菜单项）是两个不同模块，页面与 API 均不复用。
 *
 * 权限码取自 `controller.py` 的 `AuthControl(...)`（反查 `core/permission/codes.py`）：
 *   view / create / edit / delete / grant。
 */
import {Plus, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {
  type AdminMenu,
  adminMenuApi,
  type AdminMenuCreatePayload,
  type MyAdminMenus,
  roleApi,
  type RoleItem,
} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.adminMenu.title',
  permission: 'module_system:menu:view',
})

const {t} = useI18n()

/** 菜单类型下拉（value 对齐后端 `schema.py`，label 走 i18n） */
const MENU_TYPES = [
  {value: 1, labelKey: 'admin.system.adminMenu.typeDir'},
  {value: 2, labelKey: 'admin.system.adminMenu.typeMenu'},
  {value: 3, labelKey: 'admin.system.adminMenu.typeButton'},
] as const

function typeLabel(value: number): string {
  const item = MENU_TYPES.find((m) => m.value === value)
  return item ? t(item.labelKey) : String(value)
}

/** 扁平的父级候选（用于上级菜单下拉） */
interface FlatMenu {
  id: number
  title: string
  depth: number
}

function flattenMenu(nodes: AdminMenu[], depth = 0, out: FlatMenu[] = []): FlatMenu[] {
  for (const node of nodes) {
    out.push({id: node.id, title: node.title ?? node.code ?? String(node.id), depth})
    if (node.children?.length) flattenMenu(node.children, depth + 1, out)
  }
  return out
}

function collectSubtreeIds(node: AdminMenu): number[] {
  return [node.id, ...(node.children ?? []).flatMap((child) => collectSubtreeIds(child))]
}

function findSubtreeIds(nodes: AdminMenu[], id: number): number[] {
  for (const node of nodes) {
    if (node.id === id) return collectSubtreeIds(node)
  }
  for (const node of nodes) {
    if (node.children?.length) {
      const found = findSubtreeIds(node.children, id)
      if (found.length) return found
    }
  }
  return []
}

// ---------------------------------------------------------------- 只读加载
const loading = ref(false)
const failed = ref(false)
const treeData = ref<AdminMenu[]>([])
const totalMenus = ref(0)
const activeFilter = ref<boolean | undefined>(undefined)

// `/my`：当前用户可见菜单标识
const myLoaded = ref(false)
const myMenuCodes = ref<string[]>([])
const mySuperuser = ref(false)

// 角色下拉（`/system/role`）
const roleOptions = ref<RoleItem[]>([])

async function loadAll(): Promise<void> {
  loading.value = true
  failed.value = false
  // 只读加载：用 allSettled，单项失败不拖垮整页
  const [treeRes, listRes, myRes, roleRes] = await Promise.allSettled([
    adminMenuApi.tree({is_active: activeFilter.value}),
    adminMenuApi.list({is_active: activeFilter.value}),
    adminMenuApi.my(),
    roleApi.list({page: 1, page_size: 200}),
  ])

  if (treeRes.status === 'fulfilled') {
    treeData.value = treeRes.value
  } else {
    treeData.value = []
    failed.value = true
  }

  if (listRes.status === 'fulfilled') {
    totalMenus.value = listRes.value.total
  } else {
    totalMenus.value = treeData.value.length
  }

  if (myRes.status === 'fulfilled') {
    const data: MyAdminMenus = myRes.value
    myMenuCodes.value = data.menu_codes ?? []
    mySuperuser.value = Boolean(data.is_superuser)
    myLoaded.value = true
  }

  if (roleRes.status === 'fulfilled') {
    roleOptions.value = roleRes.value.items
  }

  loading.value = false
}

// ---------------------------------------------------------------- 菜单表单
const selectedId = ref<number | null>(null)
const editingId = ref<number | null>(null)
const detailLoading = ref(false)
const saving = ref(false)
const deleting = ref(false)

const form = reactive({
  code: '',
  title: '',
  parent_id: null as number | null,
  menu_type: 2,
  permission_code: '',
  sort_order: 0,
  is_active: true,
})

const parentOptions = computed<FlatMenu[]>(() => {
  const all = flattenMenu(treeData.value)
  if (editingId.value == null) return all
  // 排除自身及其子树，避免选出循环父级（后端亦会拦截）
  const excluded = new Set(findSubtreeIds(treeData.value, editingId.value))
  return all.filter((item) => !excluded.has(item.id))
})

function clearForm(): void {
  editingId.value = null
  selectedId.value = null
  Object.assign(form, {
    code: '',
    title: '',
    parent_id: null,
    menu_type: 2,
    permission_code: '',
    sort_order: 0,
    is_active: true,
  })
}

function openCreate(): void {
  clearForm()
}

async function loadMenuDetail(id: number): Promise<void> {
  detailLoading.value = true
  try {
    const detail = await adminMenuApi.detail(id)
    editingId.value = detail.id
    Object.assign(form, {
      code: detail.code ?? '',
      title: detail.title ?? '',
      parent_id: detail.parent_id ?? null,
      menu_type: detail.menu_type,
      permission_code: detail.permission_code ?? '',
      sort_order: detail.sort_order,
      is_active: detail.is_active,
    })
  } finally {
    detailLoading.value = false
  }
}

async function onSelect(data: AdminMenu): Promise<void> {
  selectedId.value = data.id
  await loadMenuDetail(data.id)
}

async function resetForm(): Promise<void> {
  if (editingId.value != null) {
    await loadMenuDetail(editingId.value)
  } else {
    clearForm()
  }
}

async function submitMenu(): Promise<void> {
  const code = form.code.trim()
  const title = form.title.trim()
  if (!code) {
    ElMessage.warning(t('admin.system.adminMenu.codeRequired'))
    return
  }
  if (!title) {
    ElMessage.warning(t('admin.system.adminMenu.titleRequired'))
    return
  }

  const payload: AdminMenuCreatePayload = {
    code,
    title,
    parent_id: form.parent_id ?? null,
    menu_type: form.menu_type,
    permission_code: form.permission_code.trim() || null,
    sort_order: form.sort_order,
    is_active: form.is_active,
  }

  saving.value = true
  try {
    if (editingId.value != null) {
      await adminMenuApi.update(editingId.value, payload)
      ElMessage.success(t('admin.system.adminMenu.saved'))
      await loadAll()
    } else {
      const created = await adminMenuApi.create(payload)
      ElMessage.success(t('admin.system.adminMenu.created'))
      await loadAll()
      selectedId.value = created.id
      await loadMenuDetail(created.id)
    }
  } finally {
    saving.value = false
  }
}

async function removeMenu(): Promise<void> {
  if (editingId.value == null) return
  const title = form.title || form.code
  try {
    await ElMessageBox.confirm(
      t('admin.system.adminMenu.removeConfirm', {title}),
      t('admin.common.notice'),
      {type: 'warning'},
    )
  } catch {
    return
  }
  deleting.value = true
  try {
    await adminMenuApi.remove(editingId.value)
    ElMessage.success(t('admin.system.adminMenu.deleted'))
    clearForm()
    await loadAll()
  } finally {
    deleting.value = false
  }
}

// ---------------------------------------------------------------- 角色菜单授权
/** el-tree 暴露给本页的方法集合（避免静态 import element-plus 类型） */
interface TreeHandle {
  getCheckedKeys: () => Array<number | string>
  getHalfCheckedKeys: () => Array<number | string>
  setCheckedKeys: (keys: number[]) => void
}

const authTreeRef = ref<TreeHandle | null>(null)
const roleId = ref<number | null>(null)
const grantLoading = ref(false)

async function loadRoleMenus(): Promise<void> {
  if (roleId.value == null) {
    authTreeRef.value?.setCheckedKeys([])
    return
  }
  grantLoading.value = true
  try {
    const ids = await adminMenuApi.roleMenuIds(roleId.value)
    authTreeRef.value?.setCheckedKeys(ids)
  } finally {
    grantLoading.value = false
  }
}

async function saveRoleMenus(): Promise<void> {
  if (roleId.value == null) {
    ElMessage.warning(t('admin.system.adminMenu.roleRequired'))
    return
  }
  const checked = (authTreeRef.value?.getCheckedKeys() ?? []).map((key) => Number(key))
  const half = (authTreeRef.value?.getHalfCheckedKeys() ?? []).map((key) => Number(key))
  const menuIds = Array.from(new Set([...checked, ...half]))

  grantLoading.value = true
  try {
    await adminMenuApi.setRoleMenus(roleId.value, menuIds)
    ElMessage.success(t('admin.system.adminMenu.grantSaved'))
  } finally {
    grantLoading.value = false
  }
}

onMounted(loadAll)
</script>

<template>
  <AdminPage :desc="$t('admin.system.adminMenu.desc')" :title="$t('admin.system.adminMenu.title')">
    <template #actions>
      <el-button
        v-auth="'module_system:menu:create'"
        :icon="Plus"
        type="primary"
        @click="openCreate"
      >
        {{ $t('admin.system.adminMenu.createMenu') }}
      </el-button>
      <el-button :icon="Refresh" :loading="loading" @click="loadAll">
        {{ $t('admin.common.refresh') }}
      </el-button>
    </template>

    <!-- 当前用户可见菜单（`/my`） -->
    <el-alert
      v-if="myLoaded"
      :closable="false"
      :title="mySuperuser
        ? $t('admin.system.adminMenu.superuserAll')
        : $t('admin.system.adminMenu.myVisible', {n: myMenuCodes.length})"
      class="mb-3"
      show-icon
      type="info"
    />

    <el-alert
      v-if="failed"
      :closable="false"
      :title="$t('admin.common.loadFailed')"
      class="mb-3"
      show-icon
      type="error"
    />

    <el-row :gutter="16">
      <!-- 左：菜单树 -->
      <el-col :span="9">
        <section class="mcard">
          <div class="mcard__head">
            <span class="mcard__title">{{ $t('admin.system.adminMenu.menuTree') }}</span>
            <div class="mcard__tools">
              <el-select
                v-model="activeFilter"
                :placeholder="$t('admin.system.adminMenu.filterActive')"
                clearable
                size="small"
                style="width: 120px"
                @change="loadAll"
              >
                <el-option :label="$t('admin.system.adminMenu.filterActiveOnly')" :value="true"/>
                <el-option :label="$t('admin.system.adminMenu.filterInactiveOnly')" :value="false"/>
              </el-select>
              <span class="hint">{{ $t('admin.system.adminMenu.totalMenus', {n: totalMenus}) }}</span>
            </div>
          </div>

          <el-tree
            v-if="treeData.length"
            :current-node-key="selectedId ?? undefined"
            :data="treeData"
            :expand-on-click-node="false"
            :props="{label: 'title', children: 'children'}"
            highlight-current
            node-key="id"
            @node-click="onSelect"
          >
            <template #default="{ data }">
              <span class="tree-node">
                <span class="tree-node__title">
                  {{ (data as AdminMenu).title || (data as AdminMenu).code }}
                </span>
                <code v-if="(data as AdminMenu).code" class="tree-node__code">
                  {{ (data as AdminMenu).code }}
                </code>
                <el-tag v-if="!(data as AdminMenu).is_active" size="small" type="info">
                  {{ $t('admin.common.disabled') }}
                </el-tag>
              </span>
            </template>
          </el-tree>
          <AdminEmpty v-else :title="$t('admin.system.adminMenu.emptyTree')"/>
        </section>
      </el-col>

      <!-- 右：菜单表单 -->
      <el-col :span="15">
        <section class="mcard">
          <div class="mcard__head">
            <span class="mcard__title">
              {{
                editingId != null
                  ? $t('admin.system.adminMenu.editMenu')
                  : $t('admin.system.adminMenu.menuForm')
              }}
            </span>
            <span v-if="editingId == null" class="hint">
              {{ $t('admin.system.adminMenu.selectHint') }}
            </span>
          </div>

          <el-form v-loading="detailLoading" :model="form" label-width="100px">
            <el-form-item :label="$t('admin.system.adminMenu.fieldCode')" required>
              <el-input
                v-model="form.code"
                :disabled="editingId != null"
                :placeholder="$t('admin.system.adminMenu.codePlaceholder')"
              />
            </el-form-item>
            <el-form-item :label="$t('admin.system.adminMenu.fieldTitle')" required>
              <el-input
                v-model="form.title"
                :placeholder="$t('admin.system.adminMenu.titlePlaceholder')"
              />
            </el-form-item>
            <el-form-item :label="$t('admin.system.adminMenu.fieldParent')">
              <el-select
                v-model="form.parent_id"
                :placeholder="$t('admin.system.adminMenu.parentPlaceholder')"
                clearable
                style="width: 100%"
              >
                <el-option
                  v-for="opt in parentOptions"
                  :key="opt.id"
                  :label="`${'— '.repeat(opt.depth)}${opt.title}`"
                  :value="opt.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('admin.system.adminMenu.fieldType')">
              <el-select v-model="form.menu_type" style="width: 100%">
                <el-option
                  v-for="item in MENU_TYPES"
                  :key="item.value"
                  :label="$t(item.labelKey)"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('admin.system.adminMenu.fieldPermission')">
              <el-input
                v-model="form.permission_code"
                :placeholder="$t('admin.system.adminMenu.permissionPlaceholder')"
              />
            </el-form-item>
            <el-form-item :label="$t('admin.system.adminMenu.fieldSort')">
              <el-input-number v-model="form.sort_order" :min="0" style="width: 100%"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.adminMenu.fieldActive')">
              <el-switch v-model="form.is_active"/>
            </el-form-item>
          </el-form>

          <div class="form-actions">
            <el-button
              v-if="editingId == null"
              v-auth="'module_system:menu:create'"
              :loading="saving"
              type="primary"
              @click="submitMenu"
            >
              {{ $t('admin.system.adminMenu.saveMenu') }}
            </el-button>
            <el-button
              v-else
              v-auth="'module_system:menu:edit'"
              :loading="saving"
              type="primary"
              @click="submitMenu"
            >
              {{ $t('admin.system.adminMenu.saveMenu') }}
            </el-button>
            <el-button @click="resetForm">
              {{ $t('admin.system.adminMenu.resetForm') }}
            </el-button>
            <el-button
              v-if="editingId != null"
              v-auth="'module_system:menu:delete'"
              :loading="deleting"
              type="danger"
              @click="removeMenu"
            >
              {{ $t('admin.common.delete') }}
            </el-button>
          </div>
        </section>
      </el-col>
    </el-row>

    <!-- 角色菜单授权 -->
    <section class="mcard mt-3">
      <div class="mcard__head">
        <span class="mcard__title">{{ $t('admin.system.adminMenu.roleGrant') }}</span>
      </div>
      <el-alert
        :closable="false"
        :title="$t('admin.system.adminMenu.grantHint')"
        class="mb-3"
        show-icon
        type="info"
      />

      <el-form inline>
        <el-form-item :label="$t('admin.system.adminMenu.roleSelect')">
          <el-select
            v-model="roleId"
            :placeholder="$t('admin.system.adminMenu.rolePlaceholder')"
            clearable
            style="width: 260px"
            @change="loadRoleMenus"
          >
            <el-option
              v-for="r in roleOptions"
              :key="r.id"
              :label="`${r.name} (${r.slug})`"
              :value="r.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :disabled="roleId == null" :loading="grantLoading" @click="loadRoleMenus">
            {{ $t('admin.system.adminMenu.loadRoleMenus') }}
          </el-button>
          <el-button
            v-auth="'module_system:menu:grant'"
            :disabled="roleId == null"
            :loading="grantLoading"
            type="primary"
            @click="saveRoleMenus"
          >
            {{ $t('admin.system.adminMenu.grantSave') }}
          </el-button>
        </el-form-item>
      </el-form>

      <el-tree
        v-if="treeData.length"
        ref="authTreeRef"
        :check-strictly="true"
        :data="treeData"
        :expand-on-click-node="false"
        :props="{label: 'title', children: 'children'}"
        class="grant-tree"
        node-key="id"
        show-checkbox
      />
      <AdminEmpty v-else :title="$t('admin.system.adminMenu.grantEmpty')"/>
    </section>
  </AdminPage>
</template>

<style scoped>
.mcard {
  padding: 16px 18px;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-line, #e5e7eb);
  border-radius: 8px;
}

.mcard__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.mcard__title {
  font-size: 15px;
  font-weight: 600;
}

.mcard__tools {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.tree-node__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-node__code {
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.form-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.grant-tree {
  max-height: 360px;
  overflow: auto;
}

.hint {
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.mb-3 {
  margin-bottom: 16px;
}

.mt-3 {
  margin-top: 16px;
}
</style>
