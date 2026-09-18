<template>
  <div class="page-container">
    <el-card shadow="never">
      <!-- 搜索区 -->
      <el-form :inline="true" :model="query" @submit.prevent="search()">
        <el-form-item label="关键词">
          <el-input
            v-model="query.keyword"
            clearable
            placeholder="用户名或邮箱"
            style="width: 220px"
            @keyup.enter="search()"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.is_active" clearable placeholder="全部" style="width: 120px">
            <el-option :value="true" label="启用"/>
            <el-option :value="false" label="停用"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="search()">查询</el-button>
          <el-button :icon="Refresh" @click="reset()">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 操作区 -->
      <div class="table-toolbar">
        <el-button v-auth="'module_system:user:create'" :icon="Plus" type="primary" @click="openCreate">
          新建用户
        </el-button>
        <span class="table-toolbar__total">共 {{ total }} 条</span>
      </div>

      <!-- 表格 -->
      <el-table v-loading="loading" :data="list" border stripe>
        <el-table-column label="ID" prop="id" width="80"/>
        <el-table-column label="用户名" min-width="140" prop="username" show-overflow-tooltip/>
        <el-table-column label="邮箱" min-width="200" prop="email" show-overflow-tooltip/>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="身份" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.is_superuser" size="small" type="danger">超管</el-tag>
            <el-tag v-else-if="row.is_staff" size="small" type="warning">员工</el-tag>
            <span v-else class="text-muted">普通</span>
          </template>
        </el-table-column>
        <el-table-column label="VIP" width="80">
          <template #default="{ row }">Lv{{ row.vip_level ?? 0 }}</template>
        </el-table-column>
        <el-table-column label="最后登录" width="170">
          <template #default="{ row }">{{ formatDateTime(row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" width="260">
          <template #default="{ row }">
            <el-button v-auth="'module_system:user:edit'" link type="primary" @click="openEdit(row as UserItem)">
              编辑
            </el-button>
            <el-button v-auth="'module_system:user:manage_roles'" link type="primary"
                       @click="openRoles(row as UserItem)">
              角色
            </el-button>
            <el-button
              v-auth="'module_system:user:edit'"
              :type="row.is_active ? 'warning' : 'success'"
              link
              @click="toggleStatus(row as UserItem)"
            >
              {{ row.is_active ? '停用' : '启用' }}
            </el-button>
            <el-button v-auth="'module_system:user:delete'" link type="danger" @click="onDelete(row as UserItem)">
              删除
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
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="isEdit" placeholder="3-30 位字母数字下划线"/>
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="user@example.com"/>
        </el-form-item>
        <el-form-item :prop="isEdit ? undefined : 'password'" label="密码">
          <el-input
            v-model="form.password"
            :placeholder="isEdit ? '留空表示不修改' : '至少 8 位'"
            show-password
            type="password"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用"/>
        </el-form-item>
        <el-form-item label="员工">
          <el-switch v-model="form.is_staff"/>
        </el-form-item>
        <el-form-item v-if="!isEdit" label="初始角色">
          <el-select v-model="form.role_ids" multiple placeholder="可多选" style="width: 100%">
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
        <el-button @click="formVisible = false">取消</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-drawer>

    <!-- 角色分配 -->
    <el-dialog v-model="rolesVisible" title="分配角色" width="480px">
      <el-alert
        :closable="false"
        class="mb-3"
        title="角色决定该用户拥有的权限码；超级管理员不受角色限制。"
        type="info"
      />
      <el-select v-model="selectedRoleIds" multiple placeholder="选择角色" style="width: 100%">
        <el-option
          v-for="role in roleOptions"
          :key="role.id"
          :label="`${role.name} (${role.slug})`"
          :value="role.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="rolesVisible = false">取消</el-button>
        <el-button :loading="saving" type="primary" @click="submitRoles">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import {Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, type FormInstance, type FormRules} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {roleApi, type RoleItem, userApi, type UserItem, type UserQuery} from '@/api'
import {useTable} from '@/hooks/useTable'
import {formatDateTime} from '@/utils/format'

/** 查询表单（在 PageQuery 基础上补齐页面字段，避免 v-model 绑到 unknown） */
interface UserQueryForm extends UserQuery {
  keyword?: string
  is_active?: boolean
}

const {
  list,
  loading,
  total,
  page,
  pageSize,
  query,
  search,
  reset,
  load,
  onPageChange,
  onSizeChange,
  remove,
} = useTable<UserItem, UserQueryForm>({
  fetcher: (params) => userApi.list(params),
  defaultQuery: {keyword: '', is_active: undefined},
})

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
    {required: true, message: '请输入用户名', trigger: 'blur'},
    {min: 3, max: 30, message: '长度 3-30', trigger: 'blur'},
    {pattern: /^[a-zA-Z0-9_]+$/, message: '仅允许字母、数字、下划线', trigger: 'blur'},
  ],
  email: [
    {required: true, message: '请输入邮箱', trigger: 'blur'},
    {type: 'email', message: '邮箱格式不正确', trigger: 'blur'},
  ],
  password: [{min: 8, message: '至少 8 位', trigger: 'blur'}],
}

const formTitle = computed(() => (isEdit.value ? '编辑用户' : '新建用户'))

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
    ElMessage.success('保存成功')
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
    `确定要${row.is_active ? '停用' : '启用'}用户「${row.username}」吗？`,
    '确认操作',
    row.is_active ? '已停用' : '已启用',
  )
}

async function onDelete(row: UserItem): Promise<void> {
  await remove(
    () => userApi.remove(row.id, false),
    `将停用用户「${row.username}」（保留数据）。如需彻底删除请联系后端用 force=true。`,
    '确认删除',
    '已停用',
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
    ElMessage.success('角色已更新')
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
  color: #6b7280;
}

.table-pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

.text-muted {
  color: #9ca3af;
}

.mb-3 {
  margin-bottom: 12px;
}
</style>
