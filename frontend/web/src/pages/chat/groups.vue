<script lang="ts" setup>
/**
 * 群聊管理（T5-11 批次 4）
 *
 * 对齐 v3 `/chat/group`：群组 CRUD + 成员管理（加人 / 改角色 / 静音 / 移出）。
 * member_count 由后端在成员增删时同步；群主不可移出（409）。
 */
import {Plus, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {chatApi, type ChatGroupItem, type ChatMemberItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.chat.title',
  permission: 'module_chat:group:view',
})

const {t} = useI18n()

interface ChatGroupQueryForm extends PageQuery {
  is_active?: boolean
}

const groupState = useAdminList<ChatGroupItem, ChatGroupQueryForm>({

  fetcher: (params) => chatApi.listGroups(params),
  defaultQuery: {is_active: undefined},
  syncUrl: true,
})

// 模板沿用原有变量名：映射为同名 ref / 函数
const list = groupState.rows
const loading = groupState.loading
const total = groupState.total
const page = groupState.page
const pageSize = groupState.pageSize
const query = groupState.query
const search = groupState.search
const reset = groupState.reset
const load = groupState.reload
const onPageChange = groupState.onPageChange
const onSizeChange = groupState.onSizeChange
const groupFailed = groupState.failed

// ---- 新建 / 编辑 ----
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive<{
  name: string;
  description: string;
  avatar: string;
  creator: number | undefined;
  is_active: boolean
}>({
  name: '',
  description: '',
  avatar: '',
  creator: undefined,
  is_active: true,
})

const formTitle = computed(() => (editingId.value ? t('admin.chat.editGroup') : t('admin.chat.createGroup')))

function openCreate() {
  editingId.value = null
  Object.assign(form, {name: '', description: '', avatar: '', creator: undefined, is_active: true})
  formVisible.value = true
}

function openEdit(row: ChatGroupItem) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name || '',
    description: row.description || '',
    avatar: row.avatar || '',
    creator: row.creator ?? undefined,
    is_active: row.is_active,
  })
  formVisible.value = true
}

async function submitForm() {
  if (!form.name.trim() || !form.creator) {
    ElMessage.warning(t('admin.chat.groupRequired'))
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      description: form.description || null,
      avatar: form.avatar || null,
      is_active: form.is_active,
    }
    if (editingId.value) {
      await chatApi.updateGroup(editingId.value, payload)
    } else {
      await chatApi.createGroup({...payload, creator: form.creator})
    }
    ElMessage.success(t('admin.common.save'))
    formVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(row: ChatGroupItem) {
  await ElMessageBox.confirm(t('admin.chat.deleteGroupConfirm'), t('admin.common.notice'), {type: 'warning'})
  await chatApi.removeGroup(row.id)
  ElMessage.success(t('admin.common.delete'))
  await load()
}

// ---- 成员管理 ----
const memberVisible = ref(false)
const memberGroup = ref<ChatGroupItem | null>(null)
const memberState = useAdminList<ChatMemberItem, PageQuery>({

  fetcher: (params) => chatApi.listMembers(memberGroup.value?.id ?? 0, params),
  immediate: false,
  pageSize: 50,
})

// 模板沿用原有变量名：映射为同名 ref / 函数
const members = memberState.rows
const memberLoading = memberState.loading
const memberTotal = memberState.total
const memberPage = memberState.page
const memberPageSize = memberState.pageSize
const memberLoad = memberState.reload
const onMemberPageChange = memberState.onPageChange
const onMemberSizeChange = memberState.onSizeChange
const memberFailed = memberState.failed

const addForm = reactive<{ user_id: number | undefined; role: string }>({user_id: undefined, role: 'member'})
const adding = ref(false)

const memberTitle = computed(() =>
  memberGroup.value ? t('admin.chat.memberTitle', {name: memberGroup.value.name || memberGroup.value.id}) : '')

function openMembers(row: ChatGroupItem) {
  memberGroup.value = row
  memberVisible.value = true
  memberLoad()
}

async function submitAdd() {
  if (!memberGroup.value || !addForm.user_id) {
    ElMessage.warning(t('admin.chat.userIdRequired'))
    return
  }
  adding.value = true
  try {
    await chatApi.addMember(memberGroup.value.id, {user_id: addForm.user_id, role: addForm.role})
    ElMessage.success(t('admin.common.save'))
    addForm.user_id = undefined
    addForm.role = 'member'
    await memberLoad()
    await load()
  } finally {
    adding.value = false
  }
}

async function onRemoveMember(row: ChatMemberItem) {
  await ElMessageBox.confirm(t('admin.chat.removeMemberConfirm'), t('admin.common.notice'), {type: 'warning'})
  await chatApi.removeMember(row.id)
  ElMessage.success(t('admin.common.delete'))
  await memberLoad()
  await load()
}

async function toggleMute(row: ChatMemberItem) {
  await chatApi.updateMember(row.id, {is_muted: !row.is_muted})
  await memberLoad()
}
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <!-- 搜索区 -->
      <el-form :inline="true" :model="query" @submit.prevent="search()">
        <el-form-item :label="$t('admin.system.sensitiveWord.keyword')">
          <el-input
            v-model="query.keyword"
            :placeholder="$t('admin.chat.namePlaceholder')"
            clearable
            style="width: 200px"
            @keyup.enter="search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="query.is_active" :placeholder="$t('admin.common.all')" clearable style="width: 110px">
            <el-option :label="$t('admin.system.sensitiveWord.active')" :value="true"/>
            <el-option :label="$t('admin.system.sensitiveWord.inactive')" :value="false"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search()">{{ $t('admin.common.search') }}</el-button>
          <el-button @click="reset()">{{ $t('admin.common.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <!-- 操作区 -->
      <div class="table-toolbar">
        <el-button v-auth="'module_chat:group:create'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.chat.createGroup') }}
        </el-button>
        <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: total}) }}</span>
      </div>

      <!-- 表格 -->
      <AdminTableSkeleton v-if="loading && !list.length" :rows="5"/>

      <AdminEmpty
        v-else-if="!loading && !list.length"
        :title="groupFailed ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
        :variant="groupFailed ? 'error' : 'default'"
      >
        <el-button v-if="groupFailed" :icon="Refresh" @click="load()">
          {{ $t('admin.common.retry') }}
        </el-button>
      </AdminEmpty>
      <el-table v-else v-loading="loading" :data="list" border stripe>
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column :label="$t('admin.common.name')" min-width="150" prop="name" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.common.description')" min-width="180" prop="description"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.chat.creator')" prop="creator" width="90"/>
        <el-table-column :label="$t('admin.chat.memberCount')" prop="member_count" width="100"/>
        <el-table-column :label="$t('admin.chat.lastMessageAt')" min-width="160" prop="last_message_at"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.common.status')" width="90">
          <template #default="{ row }">
            <el-tag :type="(row as ChatGroupItem).is_active ? 'success' : 'info'" size="small">
              {{
                (row as ChatGroupItem).is_active ? $t('admin.system.sensitiveWord.active') : $t('admin.system.sensitiveWord.inactive')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="210">
          <template #default="{ row }">
            <el-button link type="primary" @click="openMembers(row as ChatGroupItem)">
              {{ $t('admin.chat.members') }}
            </el-button>
            <el-button v-auth="'module_chat:group:edit'" link type="primary"
                       @click="openEdit(row as ChatGroupItem)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button v-auth="'module_chat:group:delete'" link type="danger"
                       @click="onDelete(row as ChatGroupItem)">
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

    <!-- 新建 / 编辑群 -->
    <el-drawer v-model="formVisible" :title="formTitle" destroy-on-close size="460px">
      <el-form :model="form" label-width="100px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="form.name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.chat.creator')" :required="!editingId">
          <el-input-number
            v-model="form.creator"
            :disabled="!!editingId"
            :min="1"
            controls-position="right"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.chat.avatar')">
          <el-input v-model="form.avatar"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="form.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-drawer>

    <!-- 成员管理 -->
    <el-drawer v-model="memberVisible" :title="memberTitle" destroy-on-close size="640px">
      <el-form :inline="true" @submit.prevent="submitAdd">
        <el-form-item :label="$t('admin.chat.userId')">
          <el-input-number v-model="addForm.user_id" :min="1" controls-position="right" style="width: 120px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.chat.role')">
          <el-select v-model="addForm.role" style="width: 110px">
            <el-option label="member" value="member"/>
            <el-option label="admin" value="admin"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button
            v-auth="'module_chat:group:manage_members'"
            :loading="adding"
            type="primary"
            @click="submitAdd"
          >
            {{ $t('admin.chat.addMember') }}
          </el-button>
        </el-form-item>
      </el-form>

      <el-table v-loading="memberLoading" :data="members" border stripe>
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column :label="$t('admin.chat.userId')" prop="user" width="90"/>
        <el-table-column :label="$t('admin.chat.role')" prop="role" width="100"/>
        <el-table-column :label="$t('admin.chat.joinedAt')" min-width="150" prop="joined_at" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.chat.muted')" width="90">
          <template #default="{ row }">
            <el-tag :type="(row as ChatMemberItem).is_muted ? 'warning' : 'success'" size="small">
              {{ (row as ChatMemberItem).is_muted ? $t('admin.common.yes') : $t('admin.common.no') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
          <template #default="{ row }">
            <el-button
              v-auth="'module_chat:group:manage_members'"
              :type="(row as ChatMemberItem).is_muted ? 'success' : 'warning'"
              link
              @click="toggleMute(row as ChatMemberItem)"
            >
              {{ (row as ChatMemberItem).is_muted ? $t('admin.chat.unmute') : $t('admin.chat.mute') }}
            </el-button>
            <el-button
              v-auth="'module_chat:group:manage_members'"
              link
              type="danger"
              @click="onRemoveMember(row as ChatMemberItem)"
            >
              {{ $t('admin.chat.remove') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        :current-page="memberPage"
        :page-size="memberPageSize"
        :total="memberTotal"
        background
        class="table-pagination"
        layout="total, prev, pager, next"
        @current-change="onMemberPageChange"
        @size-change="onMemberSizeChange"
      />
    </el-drawer>
  </div>
</template>
