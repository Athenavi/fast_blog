<template>
  <div class="page-container">
    <el-card shadow="never">
      <!-- 搜索区 -->
      <el-form :inline="true" :model="query" @submit.prevent="search()">
        <el-form-item :label="$t('admin.system.user.keyword')">
          <el-input
            v-model="query.keyword"
            clearable
            :placeholder="$t('admin.system.user.keywordPlaceholder')"
            style="width: 220px"
            @keyup.enter="search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.system.user.status')">
          <el-select v-model="query.is_active" :placeholder="$t('admin.system.user.allPlaceholder')" clearable
                     style="width: 120px">
            <el-option :label="$t('admin.system.user.activeLabel')" :value="true"/>
            <el-option :label="$t('admin.system.user.inactiveLabel')" :value="false"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="search()">{{ $t('admin.system.user.search') }}</el-button>
          <el-button :icon="Refresh" @click="reset()">{{ $t('admin.system.user.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <!-- 操作区 -->
      <div class="table-toolbar">
        <el-button v-auth="'module_system:user:create'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.system.user.createTitle') }}
        </el-button>
        <el-button :loading="exporting" @click="exportCsv">
          {{ $t('admin.common.exportCsv') }}
        </el-button>
        <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: total}) }}</span>
      </div>

      <!-- 表格 -->
      <AdminTableSkeleton v-if="loading && !list.length" :rows="5"/>

      <AdminEmpty
        v-else-if="!loading && !list.length"
        :title="failed ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
        :variant="failed ? 'error' : 'default'"
      >
        <el-button v-if="failed" :icon="Refresh" @click="load()">
          {{ $t('admin.common.retry') }}
        </el-button>
      </AdminEmpty>
      <el-table v-else v-loading="loading" :data="list" border stripe>
        <el-table-column label="ID" prop="id" width="80"/>
        <el-table-column :label="$t('admin.system.user.username')" min-width="140" prop="username"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.user.email')" min-width="200" prop="email" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.user.status')" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? t('admin.system.user.active') : t('admin.system.user.inactive') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.user.identity')" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.is_superuser" size="small" type="danger">{{ $t('admin.system.user.superuser') }}</el-tag>
            <el-tag v-else-if="row.is_staff" size="small" type="warning">{{ $t('admin.system.user.staffTag') }}</el-tag>
            <span v-else class="text-muted">{{ $t('admin.system.user.normal') }}</span>
          </template>
        </el-table-column>
        <el-table-column label="VIP" width="80">
          <template #default="{ row }">Lv{{ row.vip_level ?? 0 }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.user.lastLogin')" width="170">
          <template #default="{ row }">{{ formatDateTime(row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.user.actions')" fixed="right" width="260">
          <template #default="{ row }">
            <el-button v-auth="'module_system:user:edit'" link type="primary" @click="openEdit(row as UserItem)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button v-auth="'module_system:user:manage_roles'" link type="primary"
                       @click="openRoles(row as UserItem)">
              {{ $t('admin.system.user.assignRoles') }}
            </el-button>
            <el-button
              v-auth="'module_system:user:edit'"
              :type="row.is_active ? 'warning' : 'success'"
              link
              @click="toggleStatus(row as UserItem)"
            >
              {{ row.is_active ? t('admin.system.user.inactive') : t('admin.system.user.active') }}
            </el-button>
            <el-button v-auth="'module_system:user:delete'" link type="danger" @click="onDelete(row as UserItem)">
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        background
        class="table-pagination"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </el-card>

    <!-- 新建 / 编辑 -->
    <el-drawer v-model="formVisible" :title="formTitle" destroy-on-close size="520px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="90px">
        <el-form-item :label="$t('admin.system.user.username')" prop="username">
          <el-input v-model="form.username" :disabled="isEdit" :placeholder="$t('admin.system.user.usernameHint')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.user.email')" prop="email">
          <el-input v-model="form.email" placeholder="user@example.com"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.user.password')" :prop="isEdit ? undefined : 'password'">
          <el-input
            v-model="form.password"
            :placeholder="isEdit ? t('admin.system.user.passwordEditHint') : t('admin.system.user.passwordHint')"
            show-password
            autocomplete="new-password"
            type="password"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.system.user.status')">
          <el-switch v-model="form.is_active" :active-text="$t('admin.system.user.activeText')"
                     :inactive-text="$t('admin.system.user.inactiveText')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.user.staffLabel')">
          <el-switch v-model="form.is_staff"/>
        </el-form-item>
        <el-form-item v-if="!isEdit" :label="$t('admin.system.user.initialRoles')">
          <el-select v-model="form.role_ids" :placeholder="$t('admin.system.user.multiSelect')" multiple
                     style="width: 100%">
            <el-option
              v-for="role in roleOptions"
              :key="role.id"
              :label="`${role.name} (${role.slug})`"
              :value="role.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="formVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.system.user.save') }}</el-button>
      </template>
    </el-drawer>

    <!-- 角色分配 -->
    <el-dialog v-model="rolesVisible" :title="$t('admin.system.user.assignRoles')" width="480px">
      <el-alert
        :closable="false"
        class="mb-3"
        :title="$t('admin.system.user.assignRolesHint')"
        type="info"
      />
      <el-select v-model="selectedRoleIds" :placeholder="$t('admin.system.user.selectRoles')" multiple
                 style="width: 100%">
        <el-option
          v-for="role in roleOptions"
          :key="role.id"
          :label="`${role.name} (${role.slug})`"
          :value="role.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="rolesVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitRoles">{{ $t('admin.system.user.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.user.userManagement',
  permission: 'module_system:user:view',
})

const {t} = useI18n()
import {Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, type FormInstance, type FormRules} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {roleApi, type RoleItem, userApi, type UserItem, type UserQuery} from '@/api'
import {useAdminList} from '@/composables/useAdminList'
import {useCsvExport} from '@/composables/useCsvExport'
import {formatDateTime} from '@/utils/format'

/** 查询表单（在 PageQuery 基础上补齐页面字段，避免 v-model 绑到 unknown） */
interface UserQueryForm extends UserQuery {
  keyword?: string
  is_active?: boolean
}

const userState = useAdminList<UserItem, UserQueryForm>({
  fetcher: (params) => userApi.list(params),
  defaultQuery: {keyword: '', is_active: undefined},
  syncUrl: true,
})

// 模板沿用原有变量名：映射为同名 ref / 函数，避免整页重写带来的回归风险
const list = userState.rows
const loading = userState.loading
const failed = userState.failed
const total = userState.total
const page = userState.page
const pageSize = userState.pageSize
const query = userState.query
const search = userState.search
const reset = userState.reset
const load = userState.reload
const onPageChange = userState.onPageChange
const onSizeChange = userState.onSizeChange
const remove = userState.remove

/** 导出当前筛选条件下的全部用户（后端暂无导出端点，前端按 200/页 拉全量拼 CSV） */
const {exporting, exportCsv: runExport} = useCsvExport<UserItem>({
  filename: 'users',
  columns: [
    {key: 'id', label: 'ID'},
    {key: 'username', label: t('admin.system.user.username')},
    {key: 'email', label: t('admin.system.user.email')},
    {
      key: 'is_active',
      label: t('admin.system.user.status'),
      format: (row) => (row.is_active ? t('admin.system.user.active') : t('admin.system.user.inactive')),
    },
    {
      key: 'is_superuser',
      label: t('admin.system.user.identity'),
      format: (row) =>
        row.is_superuser
          ? t('admin.system.user.superuser')
          : row.is_staff
            ? t('admin.system.user.staffTag')
            : t('admin.system.user.normal'),
    },
    {key: 'vip_level', label: 'VIP', format: (row) => `Lv${row.vip_level ?? 0}`},
    {
      key: 'last_login_at',
      label: t('admin.system.user.lastLogin'),
      format: (row) => formatDateTime(row.last_login_at),
    },
  ],
  rows: async () => {
    const chunkSize = 200
    const first = await userApi.list({...query, page: 1, page_size: chunkSize} as UserQueryForm)
    const all: UserItem[] = [...first.items]
    const pages = Math.ceil((first.total ?? all.length) / chunkSize)
    for (let p = 2; p <= pages; p += 1) {
      const chunk = await userApi.list({...query, page: p, page_size: chunkSize} as UserQueryForm)
      all.push(...chunk.items)
    }
    return all
  },
})

async function exportCsv(): Promise<void> {
  if (await runExport()) ElMessage.success(t('admin.common.exportDone'))
}

/** 角色下拉数据（用于新建时分配与角色对话框） */
const roleOptions = ref<RoleItem[]>([])

async function loadRoles(): Promise<void> {
  try {
    const result = await roleApi.list({page: 1, page_size: 200})
    roleOptions.value = result.items
  } catch {
    roleOptions.value = []
  }
}

// ---------------------------------------------------------------- 新建 / 编辑
const formVisible = ref(false)
const saving = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  username: '',
  email: '',
  password: '',
  is_active: true,
  is_staff: false,
  role_ids: [] as number[],
})

const formRules: FormRules = {
  username: [
    {required: true, message: t('admin.system.user.usernameRequired'), trigger: 'blur'},
    {min: 3, max: 30, message: t('admin.system.user.usernameLength'), trigger: 'blur'},
    {pattern: /^[a-zA-Z0-9_]+$/, message: t('admin.system.user.usernameCharset'), trigger: 'blur'},
  ],
  email: [
    {required: true, message: t('admin.system.user.emailRequired'), trigger: 'blur'},
    {type: 'email', message: t('admin.system.user.emailInvalid'), trigger: 'blur'},
  ],
  password: [{min: 8, message: t('admin.system.user.passwordHint'), trigger: 'blur'}],
}

const formTitle = computed(() => (isEdit.value ? t('admin.system.user.editTitle') : t('admin.system.user.createTitle')))

function resetForm(): void {
  form.username = ''
  form.email = ''
  form.password = ''
  form.is_active = true
  form.is_staff = false
  form.role_ids = []
}

function openCreate(): void {
  isEdit.value = false
  editingId.value = null
  resetForm()
  formVisible.value = true
}

async function openEdit(row: UserItem): Promise<void> {
  isEdit.value = true
  editingId.value = row.id
  resetForm()
  try {
    const detail = await userApi.detail(row.id)
    form.username = detail.username
    form.email = detail.email ?? ''
    form.is_active = detail.is_active
    form.is_staff = detail.is_staff
  } catch {
    // 拦截器已提示
  }
  formVisible.value = true
}

async function submitForm(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isEdit.value && editingId.value !== null) {
      const payload: Record<string, unknown> = {
        email: form.email,
        is_active: form.is_active,
        is_staff: form.is_staff,
      }
      if (form.password) payload.password = form.password
      await userApi.update(editingId.value, payload)
    } else {
      await userApi.create({
        username: form.username,
        email: form.email,
        password: form.password,
        is_active: form.is_active,
        is_staff: form.is_staff,
        role_ids: form.role_ids,
      })
    }
    ElMessage.success(t('admin.system.user.saveSuccess'))
    formVisible.value = false
    await (isEdit.value ? load() : search())
  } catch {
    // 拦截器已提示
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------- 状态 / 删除
async function toggleStatus(row: UserItem): Promise<void> {
  await remove(
    () => userApi.setStatus(row.id, !row.is_active),
    t(row.is_active ? 'admin.system.user.confirmDisable' : 'admin.system.user.confirmEnable', {name: row.username}),
    t('admin.system.user.confirmTitle'),
    row.is_active ? t('admin.system.user.disabled') : t('admin.system.user.enabled'),
  )
}

async function onDelete(row: UserItem): Promise<void> {
  await remove(
    () => userApi.remove(row.id, false),
    t('admin.system.user.confirmRemove', {name: row.username}),
    t('admin.system.user.confirmDelete'),
    t('admin.system.user.disabled'),
  )
}

// ---------------------------------------------------------------- 角色分配
const rolesVisible = ref(false)
const selectedRoleIds = ref<number[]>([])
const roleTargetId = ref<number | null>(null)

async function openRoles(row: UserItem): Promise<void> {
  roleTargetId.value = row.id
  try {
    const roles = await userApi.roles(row.id)
    selectedRoleIds.value = roles.map((item) => item.id)
  } catch {
    selectedRoleIds.value = []
  }
  rolesVisible.value = true
}

async function submitRoles(): Promise<void> {
  if (roleTargetId.value === null) return
  saving.value = true
  try {
    await userApi.setRoles(roleTargetId.value, selectedRoleIds.value)
    ElMessage.success(t('admin.system.user.rolesUpdated'))
    rolesVisible.value = false
    await load()
  } catch {
    // 拦截器已提示
  } finally {
    saving.value = false
  }
}

onMounted(loadRoles)
</script>

<style scoped>
.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.table-toolbar__total {
  font-size: 13px;
  color: var(--color-fg-muted);
}

.table-pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

.text-muted {
  color: var(--color-fg-subtle);
}

.mb-3 {
  margin-bottom: 12px;
}
</style>
