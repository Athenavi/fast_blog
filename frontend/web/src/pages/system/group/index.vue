<script lang="ts" setup>
const {t} = useI18n()
/**
 * 权限组管理（树形列表 + 成员 / 角色绑定）
 *
 * 对齐 v3：`/system/group`。角色决定「能做什么」，权限组决定「能看谁的数据」
 * （配合 `roles.data_scope = 5` 使用）。成员与角色绑定都是**全量覆盖**语义。
 *
 * 列表用 `tree` 接口拿层级结构；关键词过滤在前端递归完成（后端 tree 只支持 is_active）。
 */
import {Delete, Edit, Key, Plus, Refresh, UserFilled} from '@element-plus/icons-vue'
import {reactive, ref} from 'vue'

import {groupApi, type GroupItem, type GroupPayload, roleApi, userApi} from '@/api'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.group.groupManagement',
  permission: 'module_system:group:view',
})

/** 选择器用的精简结构（成员来自用户接口、角色来自角色接口） */
interface PickerUser {
  id: number
  username?: string | null
  email?: string | null
}

interface PickerRole {
  id: number
  name?: string | null
  slug?: string | null
  data_scope?: number | null
}

// ---------------------------------------------------------------- 列表
const loading = ref(false)
/** 加载失败（用于错误态与重试） */
const loadFailed = ref(false)
const groups = ref<GroupItem[]>([])
const keyword = ref('')
const activeFilter = ref<boolean | undefined>(undefined)

function matches(node: GroupItem, kw: string): boolean {
  if (!kw) return true
  return [node.name, node.code, node.description]
    .some((value) => (value ?? '').toString().toLowerCase().includes(kw))
}

function filterTree(nodes: GroupItem[], kw: string): GroupItem[] {
  if (!kw) return nodes
  const result: GroupItem[] = []
  for (const node of nodes) {
    const children = filterTree(node.children ?? [], kw)
    if (matches(node, kw) || children.length) result.push({...node, children})
  }
  return result
}

const treeData = computed(() => filterTree(groups.value, keyword.value.trim().toLowerCase()))
const totalGroups = computed(() => {
  const count = (nodes: GroupItem[]): number =>
    nodes.reduce((sum, node) => sum + 1 + count(node.children ?? []), 0)
  return count(treeData.value)
})

async function loadGroups(): Promise<void> {
  loading.value = true
  try {
    groups.value = await groupApi.tree(activeFilter.value)
  } catch {
    // 失败时置错误态，避免把「请求失败」显示成「暂无数据」
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

const allNodes = computed(() => {
  const flat: GroupItem[] = []
  const walk = (nodes: GroupItem[]): void => {
    for (const node of nodes) {
      flat.push(node)
      walk(node.children ?? [])
    }
  }
  walk(groups.value)
  return flat
})

// ---------------------------------------------------------------- 新建 / 编辑
const formVisible = ref(false)
const formRef = ref()
const saving = ref(false)
const editingId = ref<number | null>(null)

function emptyForm(): GroupPayload {
  return {
    name: '',
    code: '',
    description: '',
    parent_id: null,
    sort_order: 0,
    owner_id: null,
    is_active: true,
  }
}

const form = reactive<GroupPayload>(emptyForm())

const formRules = computed(() => ({
  name: [{required: true, message: t('admin.system.group.nameRequired'), trigger: 'blur'}],
  code: [{required: true, message: t('admin.system.group.codeRequired'), trigger: 'blur'}],
}))

const formTitle = computed(() =>
  editingId.value ? t('admin.system.group.editTitle') : t('admin.system.group.createTitle'),
)

/** 上级组候选：编辑时排除自身 */
const parentOptions = computed(() => allNodes.value.filter((node) => node.id !== editingId.value))

function openCreate(parent?: GroupItem): void {
  editingId.value = null
  Object.assign(form, emptyForm(), parent ? {parent_id: parent.id} : {})
  formVisible.value = true
}

function openEdit(row: GroupItem): void {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name ?? '',
    code: row.code ?? '',
    description: row.description ?? '',
    parent_id: row.parent_id ?? null,
    sort_order: row.sort_order ?? 0,
    owner_id: row.owner_id ?? null,
    is_active: row.is_active ?? true,
  })
  formVisible.value = true
}

async function submitForm(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (editingId.value) {
      await groupApi.update(editingId.value, {...form})
      ElMessage.success(t('admin.system.group.saved'))
    } else {
      await groupApi.create({...form})
      ElMessage.success(t('admin.system.group.created'))
    }
    formVisible.value = false
    await loadGroups()
  } finally {
    saving.value = false
  }
}

async function removeGroup(row: GroupItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.system.group.deleteConfirm', {name: row.name ?? row.code ?? row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await groupApi.remove(row.id)
  ElMessage.success(t('admin.system.group.deleted'))
  await loadGroups()
}

// ---------------------------------------------------------------- 成员
const membersVisible = ref(false)
const membersGroup = ref<GroupItem | null>(null)
const memberIds = ref<number[]>([])
const memberOptions = ref<PickerUser[]>([])
const membersLoading = ref(false)
const membersSaving = ref(false)

function pickUser(user: { id: number; username?: string | null; email?: string | null }): PickerUser {
  return {id: user.id, username: user.username, email: user.email}
}

function mergeOptions(current: PickerUser[], incoming: PickerUser[]): PickerUser[] {
  const map = new Map<number, PickerUser>()
  for (const item of current) map.set(item.id, item)
  for (const item of incoming) map.set(item.id, item)
  return [...map.values()]
}

async function searchUsers(query: string): Promise<void> {
  if (!query) return
  try {
    const result = await userApi.list({keyword: query, page: 1, page_size: 20})
    memberOptions.value = mergeOptions(memberOptions.value, (result.items ?? []).map(pickUser))
  } catch {
    /* 错误提示由 request 拦截器统一处理 */
  }
}

async function openMembers(row: GroupItem): Promise<void> {
  membersVisible.value = true
  membersGroup.value = row
  membersLoading.value = true
  try {
    const [members, users] = await Promise.all([
      groupApi.members(row.id),
      userApi.list({page: 1, page_size: 20}),
    ])
    memberIds.value = (members.items ?? []).map((item) => item.id)
    memberOptions.value = mergeOptions(
      (users.items ?? []).map(pickUser),
      (members.items ?? []).map(pickUser),
    )
  } finally {
    membersLoading.value = false
  }
}

async function submitMembers(): Promise<void> {
  if (!membersGroup.value) return
  membersSaving.value = true
  try {
    await groupApi.setMembers(membersGroup.value.id, memberIds.value)
    ElMessage.success(t('admin.system.group.membersSaved'))
    membersVisible.value = false
    await loadGroups()
  } finally {
    membersSaving.value = false
  }
}

// ---------------------------------------------------------------- 角色绑定
const rolesVisible = ref(false)
const rolesGroup = ref<GroupItem | null>(null)
const roleIds = ref<number[]>([])
const roleOptions = ref<PickerRole[]>([])
const rolesLoading = ref(false)
const rolesSaving = ref(false)

async function openRoles(row: GroupItem): Promise<void> {
  rolesVisible.value = true
  rolesGroup.value = row
  rolesLoading.value = true
  try {
    const [bound, all] = await Promise.all([
      groupApi.roles(row.id),
      roleApi.list({page: 1, page_size: 200}),
    ])
    roleIds.value = (bound ?? []).map((item) => item.id)
    const map = new Map<number, PickerRole>()
    for (const role of all.items ?? []) {
      map.set(role.id, {id: role.id, name: role.name, slug: role.slug, data_scope: role.data_scope ?? null})
    }
    for (const role of bound ?? []) {
      if (!map.has(role.id)) {
        map.set(role.id, {id: role.id, name: role.name, slug: role.slug, data_scope: role.data_scope ?? null})
      }
    }
    roleOptions.value = [...map.values()]
  } finally {
    rolesLoading.value = false
  }
}

async function submitRoles(): Promise<void> {
  if (!rolesGroup.value) return
  rolesSaving.value = true
  try {
    await groupApi.setRoles(rolesGroup.value.id, roleIds.value)
    ElMessage.success(t('admin.system.group.rolesSaved'))
    rolesVisible.value = false
    await loadGroups()
  } finally {
    rolesSaving.value = false
  }
}

/** data_scope 文案（与后端 4 档一致：1 仅本人 / 2 本组及以下 / 3 全部 / 5 自定义组） */
function scopeLabel(scope?: number | null): string {
  const map: Record<number, string> = {
    1: t('admin.system.group.scopeSelf'),
    2: t('admin.system.group.scopeGroup'),
    3: t('admin.system.group.scopeAll'),
    5: t('admin.system.group.scopeCustom'),
  }
  return scope != null ? (map[scope] ?? String(scope)) : '-'
}

onMounted(loadGroups)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-form :inline="true" @submit.prevent="loadGroups">
        <el-form-item :label="$t('admin.system.group.keyword')">
          <el-input
            v-model="keyword"
            :placeholder="$t('admin.system.group.keywordPlaceholder')"
            clearable
            style="width: 200px"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="activeFilter" :placeholder="$t('admin.common.all')" clearable style="width: 130px">
            <el-option :label="$t('admin.system.group.activeLabel')" :value="true"/>
            <el-option :label="$t('admin.system.group.inactiveLabel')" :value="false"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Refresh" @click="loadGroups">{{ $t('admin.common.refresh') }}</el-button>
        </el-form-item>
      </el-form>

      <div class="table-toolbar">
        <el-button v-auth="'module_system:group:create'" :icon="Plus" type="primary" @click="openCreate()">
          {{ $t('admin.system.group.createTitle') }}
        </el-button>
        <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: totalGroups}) }}</span>
      </div>

      <AdminTableSkeleton v-if="loading && !treeData.length" :rows="5"/>

      <AdminEmpty
        v-else-if="!loading && !treeData.length"
        :title="loadFailed ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
        :variant="loadFailed ? 'error' : 'default'"
      >
        <el-button v-if="loadFailed" :icon="Refresh" @click="loadGroups()">
          {{ $t('admin.common.retry') }}
        </el-button>
      </AdminEmpty>

      <el-table v-else v-loading="loading" :data="treeData"
        :tree-props="{children: 'children'}"
        border
        default-expand-all
                row-key="id">
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column :label="$t('admin.common.name')" min-width="180" prop="name" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="name-cell">{{ row.name }}</span>
            <el-tag v-if="!row.is_active" class="ml-1" size="small" type="info">
              {{ $t('admin.system.group.inactiveLabel') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.group.code')" min-width="140" prop="code"/>
        <el-table-column :label="$t('admin.common.description')" min-width="200" prop="description"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.group.memberCount')" width="100">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.member_count ?? 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.group.sortOrder')" prop="sort_order" width="80"/>
        <el-table-column :label="$t('admin.common.updatedAt')" width="170">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="300">
          <template #default="{ row }">
            <el-button v-auth="'module_system:group:manage_members'" :icon="UserFilled" link type="primary"
                       @click="openMembers(row as GroupItem)">
              {{ $t('admin.system.group.members') }}
            </el-button>
            <el-button v-auth="'module_system:group:manage_roles'" :icon="Key" link type="primary"
                       @click="openRoles(row as GroupItem)">
              {{ $t('admin.system.group.roles') }}
            </el-button>
            <el-button v-auth="'module_system:group:edit'" :icon="Edit" link type="primary"
                       @click="openEdit(row as GroupItem)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button v-auth="'module_system:group:delete'" :icon="Delete" link type="danger"
                       @click="removeGroup(row as GroupItem)">
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建 / 编辑 -->
    <el-dialog v-model="formVisible" :title="formTitle" destroy-on-close width="560px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="90px">
        <el-form-item :label="$t('admin.common.name')" prop="name">
          <el-input v-model="form.name" maxlength="100" show-word-limit/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.group.code')" prop="code">
          <el-input v-model="form.code" :placeholder="$t('admin.system.group.codePlaceholder')" maxlength="100"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.group.parent')">
          <el-select v-model="form.parent_id" :placeholder="$t('admin.system.group.topLevel')" clearable
                     style="width: 100%">
            <el-option v-for="node in parentOptions" :key="node.id" :label="node.name ?? ''" :value="node.id"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description" :rows="2" maxlength="255" show-word-limit type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.group.sortOrder')">
          <el-input-number v-model="form.sort_order" :min="0"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.enabled')">
          <el-switch v-model="form.is_active"/>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="formVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- 成员 -->
    <el-dialog v-model="membersVisible" :title="$t('admin.system.group.membersTitle', {name: membersGroup?.name ?? ''})" destroy-on-close
               width="560px">
      <el-alert :closable="false" :title="$t('admin.system.group.membersHint')" class="page-alert" show-icon
                type="info"/>
      <el-select
        v-model="memberIds"
        :loading="membersLoading"
        :placeholder="$t('admin.system.group.selectMembers')"
        :remote-method="searchUsers"
        filterable
        multiple
        remote
        remote-show-suffix
        style="width: 100%"
      >
        <el-option
          v-for="user in memberOptions"
          :key="user.id"
          :label="user.username ? `${user.username}${user.email ? ' <' + user.email + '>' : ''}` : String(user.id)"
          :value="user.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="membersVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="membersSaving" type="primary" @click="submitMembers">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 角色绑定 -->
    <el-dialog v-model="rolesVisible" :title="$t('admin.system.group.rolesTitle', {name: rolesGroup?.name ?? ''})" destroy-on-close
               width="560px">
      <el-alert :closable="false" :title="$t('admin.system.group.rolesHint')" class="page-alert" show-icon
                type="info"/>
      <el-select v-model="roleIds" :loading="rolesLoading" :placeholder="$t('admin.system.group.selectRoles')" multiple
                 style="width: 100%">
        <el-option
          v-for="role in roleOptions"
          :key="role.id"
          :label="`${role.name ?? role.slug ?? role.id}（${scopeLabel(role.data_scope)}）`"
          :value="role.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="rolesVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="rolesSaving" type="primary" @click="submitRoles">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.name-cell {
  font-weight: 500;
}

.ml-1 {
  margin-left: 4px;
}
</style>
