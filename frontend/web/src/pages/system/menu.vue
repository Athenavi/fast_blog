<script lang="ts" setup>
const {t} = useI18n()
/**
 * 前台导航菜单管理
 *
 * 与「后台菜单」的区别：这里是**前台**展示用的导航（`menus` / `menu_items`，
 * 按位置供主题渲染）；后台侧边栏的授权菜单是 `admin_menus`。
 * 因此权限码用 `module_system:navmenu:*`。
 */
import {Delete, Edit, Plus, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {reactive, ref} from 'vue'

import {menuApi, type MenuItemNode, type MenuNode} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: t('admin.system.menu.title'),
  permission: 'module_system:navmenu:view',
})

const TARGETS = [
  {label: t('admin.system.menu.targetSelf'), value: '_self'},
  {label: t('admin.system.menu.targetBlank'), value: '_blank'},
]

// ---------------------------------------------------------------- 菜单容器
const loading = ref(false)
const menus = ref<MenuNode[]>([])
const total = ref(0)
const activeMenuId = ref<number | null>(null)

async function loadMenus(): Promise<void> {
  loading.value = true
  try {
    const data = await menuApi.list()
    menus.value = data.items
    total.value = data.total
    if (!menus.value.some((item) => item.id === activeMenuId.value)) {
      activeMenuId.value = menus.value[0]?.id ?? null
    }
    await loadItems()
  } finally {
    loading.value = false
  }
}

function selectMenu(id: number): void {
  activeMenuId.value = id
  loadItems()
}

// ---------------------------------------------------------------- 菜单项
const items = ref<MenuItemNode[]>([])
const itemsLoading = ref(false)

async function loadItems(): Promise<void> {
  if (!activeMenuId.value) {
    items.value = []
    return
  }
  itemsLoading.value = true
  try {
    const detail = await menuApi.detail(activeMenuId.value)
    items.value = detail.items ?? []
  } catch {
    items.value = []
  } finally {
    itemsLoading.value = false
  }
}

const menuDialog = ref(false)
const menuSaving = ref(false)
const editingMenuId = ref<number | null>(null)
const menuForm = reactive({name: '', slug: '', description: '', is_active: true})

function openMenuCreate(): void {
  editingMenuId.value = null
  Object.assign(menuForm, {name: '', slug: '', description: '', is_active: true})
  menuDialog.value = true
}

function openMenuEdit(row: MenuNode): void {
  editingMenuId.value = row.id
  Object.assign(menuForm, {
    name: row.name,
    slug: row.slug,
    description: row.description ?? '',
    is_active: row.is_active,
  })
  menuDialog.value = true
}

async function submitMenu(): Promise<void> {
  const name = menuForm.name.trim()
  const slug = menuForm.slug.trim()
  if (!name || !slug) {
    ElMessage.warning(t('admin.system.menu.nameAndCodeRequired'))
    return
  }

  menuSaving.value = true
  try {
    if (editingMenuId.value) {
      await menuApi.update(editingMenuId.value, {
        name,
        description: menuForm.description,
        is_active: menuForm.is_active,
      })
      ElMessage.success(t('admin.system.menu.saved'))
    } else {
      const created = await menuApi.create({name, slug, description: menuForm.description})
      ElMessage.success(t('admin.system.menu.created'))
      activeMenuId.value = created.id
    }
    menuDialog.value = false
    await loadMenus()
  } finally {
    menuSaving.value = false
  }
}

async function removeMenu(row: MenuNode): Promise<void> {
  await ElMessageBox.confirm(t('admin.system.menu.confirmRemoveMenu', {name: row.name}), t('admin.common.notice'), {
    type: 'warning',
  })
  await menuApi.remove(row.id)
  ElMessage.success(t('admin.system.menu.deleted'))
  await loadMenus()
}

// ---------------------------------------------------------------- 菜单项编辑
const itemDialog = ref(false)
const itemSaving = ref(false)
const editingItemId = ref<number | null>(null)
const itemForm = reactive({
  title: '',
  url: '',
  parent_id: null as number | null,
  target: '_self',
  order_index: 0,
  is_active: true,
})

/** 只允许挂到顶级项下（两级导航足够，且与前台渲染方式一致） */
const parentOptions = computed(() => items.value.filter((item) => item.id !== editingItemId.value))

function openItemCreate(parent?: MenuItemNode): void {
  editingItemId.value = null
  Object.assign(itemForm, {
    title: '',
    url: '',
    parent_id: parent?.id ?? null,
    target: '_self',
    order_index: 0,
    is_active: true,
  })
  itemDialog.value = true
}

function openItemEdit(row: MenuItemNode): void {
  editingItemId.value = row.id
  Object.assign(itemForm, {
    title: row.title,
    url: row.url ?? '',
    parent_id: row.parent_id ?? null,
    target: row.target ?? '_self',
    order_index: row.order_index ?? 0,
    is_active: row.is_active,
  })
  itemDialog.value = true
}

async function submitItem(): Promise<void> {
  const title = itemForm.title.trim()
  if (!title) {
    ElMessage.warning(t('admin.system.menu.itemTitleRequired'))
    return
  }
  if (!activeMenuId.value) {
    ElMessage.warning(t('admin.system.menu.menuRequired'))
    return
  }

  itemSaving.value = true
  try {
    const payload = {
      title,
      url: itemForm.url.trim(),
      parent_id: itemForm.parent_id,
      target: itemForm.target,
      order_index: itemForm.order_index,
      is_active: itemForm.is_active,
    }
    if (editingItemId.value) {
      await menuApi.updateItem(editingItemId.value, payload)
      ElMessage.success(t('admin.system.menu.saved'))
    } else {
      await menuApi.addItem(activeMenuId.value, payload)
      ElMessage.success(t('admin.system.menu.created'))
    }
    itemDialog.value = false
    await loadItems()
  } finally {
    itemSaving.value = false
  }
}

async function removeItem(row: MenuItemNode): Promise<void> {
  await ElMessageBox.confirm(t('admin.system.menu.confirmRemoveItem', {title: row.title}), t('admin.common.notice'), {type: 'warning'})
  await menuApi.removeItem(row.id)
  ElMessage.success(t('admin.system.menu.deleted'))
  await loadItems()
}

onMounted(loadMenus)
</script>

<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>{{ $t('admin.system.menu.navMenus') }}</span>
              <el-button v-auth="'module_system:navmenu:create'" :icon="Plus" link type="primary"
                         @click="openMenuCreate">
                {{ $t('admin.common.create') }}
              </el-button>
            </div>
          </template>

          <div v-loading="loading" class="menu-list">
            <div
              v-for="menu in menus"
              :key="menu.id"
              :class="{active: menu.id === activeMenuId}"
              class="menu-item"
              @click="selectMenu(menu.id)"
            >
              <div class="menu-meta">
                <span class="menu-name">{{ menu.name }}</span>
                <code class="menu-slug">{{ menu.slug }}</code>
              </div>
              <div class="menu-actions" @click.stop>
                <el-tag v-if="!menu.is_active" size="small" type="info">{{ $t('admin.common.disabled') }}</el-tag>
                <el-button v-auth="'module_system:navmenu:edit'" :icon="Edit" link type="primary"
                           @click="openMenuEdit(menu)"/>
                <el-button v-auth="'module_system:navmenu:delete'" :icon="Delete" link type="danger"
                           @click="removeMenu(menu)"/>
              </div>
            </div>
            <el-empty v-if="!loading && !menus.length" :description="$t('admin.system.menu.emptyMenus')"/>
          </div>

          <p class="hint">共 {{ total }} 个菜单</p>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>{{ $t('admin.system.menu.menuItems') }}</span>
              <div>
                <el-button
                  v-auth="'module_system:navmenu:create'"
                  :disabled="!activeMenuId"
                  :icon="Plus"
                  link
                  type="primary"
                  @click="openItemCreate()"
                >
                  {{ $t('admin.system.menu.createItem') }}
                </el-button>
                <el-button :icon="Refresh" link @click="loadItems"/>
              </div>
            </div>
          </template>

          <el-table
            v-loading="itemsLoading"
            :data="items"
            :tree-props="{children: 'children'}"
            default-expand-all
            row-key="id"
          >
            <el-table-column :label="$t('admin.system.menu.itemTitle')" min-width="180" prop="title"/>
            <el-table-column :label="$t('admin.system.menu.itemUrl')" min-width="200" prop="url" show-overflow-tooltip/>
            <el-table-column :label="$t('admin.system.menu.itemTarget')" width="110">
              <template #default="{row}">
                {{ row.target === '_blank' ? t('admin.system.menu.targetBlank') : t('admin.system.menu.targetSelf') }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.system.menu.itemOrder')" prop="order_index" width="80"/>
            <el-table-column :label="$t('admin.common.enabled')" width="80">
              <template #default="{row}">
                <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                  {{ row.is_active ? t('admin.common.yes') : t('admin.common.no') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="200">
              <template #default="{row}">
                <el-button
                  v-auth="'module_system:navmenu:create'"
                  :disabled="Boolean(row.parent_id)"
                  link
                  type="primary"
                  @click="openItemCreate(row)"
                >
                  {{ $t('admin.system.menu.childItems') }}
                </el-button>
                <el-button v-auth="'module_system:navmenu:edit'" :icon="Edit" link type="primary"
                           @click="openItemEdit(row)">
                  {{ $t('admin.common.edit') }}
                </el-button>
                <el-button v-auth="'module_system:navmenu:delete'" :icon="Delete" link type="danger"
                           @click="removeItem(row)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="!itemsLoading && !items.length" :description="$t('admin.system.menu.emptyItems')"/>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog
      v-model="menuDialog"
      :title="editingMenuId ? t('admin.system.menu.editMenu') : t('admin.system.menu.createMenu')"
      destroy-on-close
      width="520px"
    >
      <el-form :model="menuForm" label-width="90px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="menuForm.name" :placeholder="$t('admin.system.menu.namePlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.menu.code')" required>
          <el-input v-model="menuForm.slug" :disabled="Boolean(editingMenuId)"
                    :placeholder="$t('admin.system.menu.codePlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="menuForm.description" :rows="2" type="textarea"/>
        </el-form-item>
        <el-form-item v-if="editingMenuId" :label="$t('admin.common.enabled')">
          <el-switch v-model="menuForm.is_active"/>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="menuDialog = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="menuSaving" type="primary" @click="submitMenu">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="itemDialog"
      :title="editingItemId ? t('admin.system.menu.editItem') : t('admin.system.menu.createItem')"
      destroy-on-close
      width="520px"
    >
      <el-form :model="itemForm" label-width="90px">
        <el-form-item :label="$t('admin.system.menu.itemTitle')" required>
          <el-input v-model="itemForm.title"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.menu.itemUrl')">
          <el-input v-model="itemForm.url" :placeholder="$t('admin.system.menu.urlPlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.menu.parent')">
          <el-select v-model="itemForm.parent_id" :placeholder="$t('admin.system.menu.parentPlaceholder')" clearable
                     style="width: 100%">
            <el-option v-for="item in parentOptions" :key="item.id" :label="item.title" :value="item.id"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.system.menu.itemTarget')">
          <el-select v-model="itemForm.target" style="width: 100%">
            <el-option v-for="item in TARGETS" :key="item.value" :label="item.label" :value="item.value"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.system.menu.itemOrder')">
          <el-input-number v-model="itemForm.order_index" :min="0"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.enabled')">
          <el-switch v-model="itemForm.is_active"/>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="itemDialog = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="itemSaving" type="primary" @click="submitItem">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.menu-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 60px;
}

.menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.menu-item:hover {
  border-color: #c6e2ff;
}

.menu-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.menu-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.menu-name {
  font-weight: 500;
}

.menu-slug {
  font-size: 12px;
  color: #909399;
}

.menu-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.hint {
  margin: 12px 0 0;
  font-size: 12px;
  color: #909399;
}
</style>
