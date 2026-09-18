<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-form :inline="true" @submit.prevent="search()">
        <el-form-item :label="$t('admin.system.role.keyword')">
          <el-input
            v-model="query.keyword"
            clearable
            :placeholder="$t('admin.system.role.keywordPlaceholder')"
            style="width: 200px"
            @keyup.enter="search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.system.role.type')">
          <el-select v-model="query.is_system" :placeholder="$t('admin.common.all')" clearable style="width: 130px">
            <el-option :label="$t('admin.system.role.builtinLabel')" :value="true"/>
            <el-option :label="$t('admin.system.role.customLabel')" :value="false"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="search()">{{ $t('admin.common.search') }}</el-button>
          <el-button :icon="Refresh" @click="reset()">{{ $t('admin.common.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <div class="table-toolbar">
        <el-button v-auth="'module_system:role:edit'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.system.role.createTitle') }}
        </el-button>
        <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: total}) }}</span>
      </div>

      <el-table v-loading="loading" :data="list" border stripe>
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column :label="$t('admin.common.name')" min-width="140" prop="name" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.role.code')" prop="slug" width="150"/>
        <el-table-column :label="$t('admin.common.description')" min-width="200" prop="description"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.role.type')" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_system" size="small" type="warning">{{ $t('admin.system.role.builtinTag') }}</el-tag>
            <el-tag v-else size="small" type="info">{{ $t('admin.system.role.customTag') }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.role.permissionCount')" prop="permission_count" width="90"/>
        <el-table-column :label="$t('admin.system.role.userCount')" prop="user_count" width="90"/>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="230">
          <template #default="{ row }">
            <el-button link type="primary" @click="openPermissions(row as RoleItem)">
              {{ $t('admin.system.role.permissionConfig') }}
            </el-button>
            <el-button v-auth="'module_system:role:edit'" link type="primary" @click="openEdit(row as RoleItem)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button
              v-auth="'module_system:role:edit'"
              :disabled="row.is_system"
              link
              type="danger"
              @click="onDelete(row as RoleItem)"
            >
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

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
    <el-dialog v-model="formVisible" :title="formTitle" destroy-on-close width="520px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="90px">
        <el-form-item :label="$t('admin.common.name')" prop="name">
          <el-input v-model="form.name" :placeholder="$t('admin.system.role.namePlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.role.code')" prop="slug">
          <el-input v-model="form.slug" :disabled="isEdit" :placeholder="$t('admin.system.role.codePlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description" :rows="2" type="textarea"/>
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

    <!-- 权限配置 -->
    <el-drawer v-model="permVisible" :title="permTitle" destroy-on-close size="560px">
      <el-alert
        :closable="false"
        class="mb-3"
        :title="$t('admin.system.role.permissionHint')"
        type="info"
      />

      <div v-loading="permLoading" class="perm">
        <el-collapse v-model="activeGroups">
          <el-collapse-item
            v-for="group in groupedCapabilities"
            :key="group.resource_type"
            :name="group.resource_type"
          >
            <template #title>
              <span class="perm__title">{{ group.resource_type }}</span>
              <el-tag class="perm__count" size="small">
                {{ countChecked(group) }} / {{ group.capabilities.length }}
              </el-tag>
            </template>
            <el-checkbox-group v-model="checkedCodes" class="perm__group">
              <el-checkbox
                v-for="cap in group.capabilities"
                :key="cap.code"
                :label="cap.code"
                :value="cap.code"
              >
                {{ cap.name }} <span class="perm__code">{{ cap.code }}</span>
              </el-checkbox>
            </el-checkbox-group>
          </el-collapse-item>
        </el-collapse>
      </div>

      <template #footer>
        <el-button @click="permVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitPermissions">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script lang="ts" setup>
const {t} = useI18n()
import {Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, type FormInstance, type FormRules} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {type CapabilityGroup, permissionApi, roleApi, type RoleItem, type RoleQuery,} from '@/api'
import {useTable} from '@/hooks/useTable'

/** 查询表单（在 PageQuery 基础上补齐页面字段，避免 v-model 绑到 unknown） */
interface RoleQueryForm extends RoleQuery {
  keyword?: string
  is_system?: boolean
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
} = useTable<RoleItem, RoleQueryForm>({
  fetcher: (params) => roleApi.list(params),
  defaultQuery: {keyword: '', is_system: undefined},
})

// ---------------------------------------------------------------- 新建 / 编辑
const formVisible = ref(false)
const saving = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  slug: '',
  description: '',
  is_active: true,
})

const formRules: FormRules = {
  name: [{required: true, message: t('admin.system.role.nameRequired'), trigger: 'blur'}],
  slug: [
    {required: true, message: t('admin.system.role.codeRequired'), trigger: 'blur'},
    {pattern: /^[a-z0-9_-]+$/, message: t('admin.system.role.codeCharset'), trigger: 'blur'},
  ],
}

const formTitle = computed(() => (isEdit.value ? t('admin.system.role.editTitle') : t('admin.system.role.createTitle')))

function openCreate(): void {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, {name: '', slug: '', description: '', is_active: true})
  formVisible.value = true
}

async function openEdit(row: RoleItem): Promise<void> {
  isEdit.value = true
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    slug: row.slug,
    description: row.description ?? '',
    is_active: row.is_active,
  })
  formVisible.value = true
}

async function submitForm(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isEdit.value && editingId.value !== null) {
      await roleApi.update(editingId.value, {
        name: form.name,
        description: form.description,
        is_active: form.is_active,
      })
    } else {
      await roleApi.create({
        name: form.name,
        slug: form.slug,
        description: form.description,
      })
    }
    ElMessage.success(t('admin.system.role.saveSuccess'))
    formVisible.value = false
    await (isEdit.value ? load() : search())
  } catch {
    // 拦截器已提示
  } finally {
    saving.value = false
  }
}

async function onDelete(row: RoleItem): Promise<void> {
  await remove(
    () => roleApi.remove(row.id),
    t('admin.system.role.confirmDelete', {name: row.name}),
    t('admin.system.role.confirmDelete'),
  )
}

// ---------------------------------------------------------------- 权限配置
const permVisible = ref(false)
const permLoading = ref(false)
const permTarget = ref<RoleItem | null>(null)
const groupedCapabilities = ref<CapabilityGroup[]>([])
const checkedCodes = ref<string[]>([])
const activeGroups = ref<string[]>([])

const permTitle = computed(() =>
  permTarget.value ? t('admin.system.role.permissionConfigFor', {name: permTarget.value.name}) : t('admin.system.role.permissionConfigTitle'),
)

function countChecked(group: CapabilityGroup): number {
  const codes = new Set(group.capabilities.map((cap) => cap.code))
  return checkedCodes.value.filter((code) => codes.has(code)).length
}

async function openPermissions(row: RoleItem): Promise<void> {
  permTarget.value = row
  permVisible.value = true
  permLoading.value = true
  try {
    const [groups, owned] = await Promise.all([
      permissionApi.grouped(),
      roleApi.permissions(row.id),
    ])
    groupedCapabilities.value = groups
    checkedCodes.value = owned
    activeGroups.value = groups.slice(0, 2).map((group) => group.resource_type)
  } catch {
    groupedCapabilities.value = []
    checkedCodes.value = []
  } finally {
    permLoading.value = false
  }
}

async function submitPermissions(): Promise<void> {
  if (!permTarget.value) return
  saving.value = true
  try {
    await roleApi.setPermissions(permTarget.value.id, checkedCodes.value)
    ElMessage.success(t('admin.system.role.permissionsUpdated'))
    permVisible.value = false
    await load()
  } catch {
    // 拦截器已提示
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  // 首次进入时预热权限码分组（供权限抽屉使用）
  permissionApi
    .grouped()
    .then((groups) => {
      groupedCapabilities.value = groups
    })
    .catch(() => undefined)
})
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

.perm {
  min-height: 200px;
}

.perm__title {
  margin-right: 10px;
  font-weight: 600;
}

.perm__count {
  margin-left: 6px;
}

.perm__group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.perm__code {
  color: #9ca3af;
  font-size: 12px;
  margin-left: 4px;
}

.mb-3 {
  margin-bottom: 12px;
}
</style>
