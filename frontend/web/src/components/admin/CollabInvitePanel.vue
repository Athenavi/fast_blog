<script lang="ts" setup>
/**
 * 协作管理 · 协作邀请面板
 *
 * 从 `pages/content/collaboration.vue` 的「协作邀请」标签页抽出：邀请列表（筛选 /
 * 新建 / 撤销）、以及顶部的"用邀请码接受邀请"。
 *
 * 与页面之间只需要两件事：
 *  - `workspaceId`：新建邀请时把它作为默认目标（原实现是读页面的 `currentWorkspaceId`）；
 *  - `accepted` 事件：接受邀请可能让你加入一个新工作区，而工作区列表现在住在
 *    `CollabWorkspacePanel` 里，本组件够不着，只能请页面去刷新它。
 *
 * 加载时机与原实现一致：`useAdminList` 默认挂载即加载（这里没设 `immediate: false`），
 * 而原页面的 `onTabChange` 从未为邀请标签页做过任何事。
 */
import {Delete, Plus, Refresh, Search} from '@element-plus/icons-vue'
import {reactive, ref} from 'vue'

import {collaborationApi, type InviteItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

const props = defineProps<{
  /** 当前选中的工作区 id：新建邀请时作为默认目标 */
  workspaceId: number | null
}>()

const emit = defineEmits<{
  /** 接受邀请成功 —— 页面需要据此刷新工作区列表（可能加入了新工作区） */
  (e: 'accepted'): void
}>()

const {t} = useI18n()

const inviteState = useAdminList<InviteItem, PageQuery & { target_type?: string }>({
  fetcher: (params) => collaborationApi.listInvites(params),
  defaultQuery: {keyword: '', target_type: ''},
  syncUrl: true,
})

// 模板沿用原有变量名：映射为同名 ref / 函数
const inviteList = inviteState.rows
const inviteLoading = inviteState.loading
const inviteTotal = inviteState.total
const invitePage = inviteState.page
const invitePageSize = inviteState.pageSize
const inviteQuery = inviteState.query
const inviteSearch = inviteState.search
const inviteReset = inviteState.reset
const inviteLoad = inviteState.reload
const onInvitePageChange = inviteState.onPageChange
const onInviteSizeChange = inviteState.onSizeChange

const inviteFormVisible = ref(false)
const inviteSaving = ref(false)
const inviteForm = reactive({
  target_type: 'workspace' as string,
  target_id: undefined as number | undefined,
  permission: 'edit',
  expire_hours: 24,
  max_uses: 0,
})

function openInviteCreate(): void {
  Object.assign(inviteForm, {
    target_type: 'workspace',
    // 默认指到当前工作区，省掉一次手输
    target_id: props.workspaceId ?? undefined,
    permission: 'edit',
    expire_hours: 24,
    max_uses: 0,
  })
  inviteFormVisible.value = true
}

async function submitInvite(): Promise<void> {
  if (inviteForm.target_id === undefined) {
    ElMessage.warning(t('admin.content.collaboration.targetIdRequired'))
    return
  }
  inviteSaving.value = true
  try {
    const created = await collaborationApi.createInvite({
      target_type: inviteForm.target_type as never,
      target_id: inviteForm.target_id,
      permission: inviteForm.permission,
      expire_hours: inviteForm.expire_hours,
      max_uses: inviteForm.max_uses,
    })
    inviteFormVisible.value = false
    await inviteLoad()
    // 邀请码只在创建响应里出现，用弹窗把它完整展示出来
    ElMessageBox.alert(
      t('admin.content.collaboration.inviteCreatedHint', {code: created.invite_code || ''}),
      t('admin.common.notice'),
    ).catch(() => undefined)
  } finally {
    inviteSaving.value = false
  }
}

async function onRevokeInvite(row: InviteItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.content.collaboration.revokeConfirm', {name: row.invite_code || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await collaborationApi.revokeInvite(row.id)
  ElMessage.success(t('admin.common.delete'))
  await inviteLoad()
}

const acceptCode = ref('')
const accepting = ref(false)

async function onAcceptInvite(): Promise<void> {
  if (!acceptCode.value.trim()) {
    ElMessage.warning(t('admin.content.collaboration.codeRequired'))
    return
  }
  accepting.value = true
  try {
    await collaborationApi.acceptInvite(acceptCode.value.trim())
    ElMessage.success(t('admin.content.collaboration.accepted'))
    acceptCode.value = ''
    // 接受邀请可能让你加入一个新工作区：请页面去刷新工作区面板
    emit('accepted')
    await inviteLoad()
  } finally {
    accepting.value = false
  }
}
</script>

<template>
  <el-card shadow="never">
    <el-form :inline="true" :model="inviteQuery" @submit.prevent="inviteSearch()">
      <el-form-item :label="$t('admin.content.collaboration.keyword')">
        <el-input v-model="inviteQuery.keyword" clearable style="width: 180px"
                  @keyup.enter="inviteSearch()"/>
      </el-form-item>
      <el-form-item :label="$t('admin.content.collaboration.targetType')">
        <el-select v-model="inviteQuery.target_type" clearable style="width: 150px">
          <el-option label="article" value="article"/>
          <el-option label="workspace" value="workspace"/>
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button :icon="Search" type="primary" @click="inviteSearch()">
          {{ $t('admin.common.search') }}
        </el-button>
        <el-button :icon="Refresh" @click="inviteReset()">{{ $t('admin.common.reset') }}</el-button>
      </el-form-item>
    </el-form>

    <div class="table-toolbar">
      <el-button v-auth="'module_content:collaboration:create'" :icon="Plus" type="primary"
                 @click="openInviteCreate">
        {{ $t('admin.content.collaboration.createInvite') }}
      </el-button>
      <el-input v-model="acceptCode" :placeholder="$t('admin.content.collaboration.acceptPlaceholder')"
                style="width: 280px"/>
      <el-button v-auth="'module_content:collaboration:create'" :loading="accepting"
                 @click="onAcceptInvite">
        {{ $t('admin.content.collaboration.accept') }}
      </el-button>
      <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: inviteTotal}) }}</span>
    </div>

    <el-table v-loading="inviteLoading" :data="inviteList" border stripe>
      <el-table-column :label="$t('admin.content.collaboration.inviteCode')" min-width="240"
                       prop="invite_code" show-overflow-tooltip/>
      <el-table-column :label="$t('admin.content.collaboration.targetType')" prop="target_type"
                       width="120"/>
      <el-table-column :label="$t('admin.content.collaboration.targetId')" prop="target_id" width="100"/>
      <el-table-column :label="$t('admin.content.collaboration.permission')" prop="permission"
                       width="100"/>
      <el-table-column :label="$t('admin.content.collaboration.usage')" align="center" width="110">
        <template #default="{ row }">
          {{ (row as InviteItem).use_count }}/{{ (row as InviteItem).max_uses || '∞' }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.content.collaboration.expiresAt')" min-width="170"
                       prop="expires_at"/>
      <el-table-column :label="$t('admin.common.status')" align="center" width="100">
        <template #default="{ row }">
          <el-tag :type="(row as InviteItem).is_active ? 'success' : 'info'" size="small">
            {{ (row as InviteItem).is_active ? $t('admin.common.enabled') : $t('admin.common.disabled') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="120">
        <template #default="{ row }">
          <el-button v-auth="'module_content:collaboration:delete'"
                     :disabled="!(row as InviteItem).is_active" :icon="Delete" link type="danger"
                     @click="onRevokeInvite(row as InviteItem)">
            {{ $t('admin.content.collaboration.revoke') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination :current-page="invitePage" :page-size="invitePageSize"
                   :page-sizes="[10, 20, 50, 100]" :total="inviteTotal" background
                   class="table-pagination" layout="total, sizes, prev, pager, next, jumper"
                   @current-change="onInvitePageChange" @size-change="onInviteSizeChange"/>
  </el-card>

  <!-- 邀请表单 -->
  <el-dialog v-model="inviteFormVisible" :title="$t('admin.content.collaboration.createInvite')"
             width="460px">
    <el-form :model="inviteForm" label-width="120px">
      <el-form-item :label="$t('admin.content.collaboration.targetType')" required>
        <el-select v-model="inviteForm.target_type" style="width: 100%">
          <el-option label="workspace" value="workspace"/>
          <el-option label="article" value="article"/>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('admin.content.collaboration.targetId')" required>
        <el-input-number v-model="inviteForm.target_id" :min="1" style="width: 100%"/>
      </el-form-item>
      <el-form-item :label="$t('admin.content.collaboration.permission')">
        <el-select v-model="inviteForm.permission" style="width: 100%">
          <el-option label="edit" value="edit"/>
          <el-option label="view" value="view"/>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('admin.content.collaboration.expireHours')">
        <el-input-number v-model="inviteForm.expire_hours" :max="720" :min="1" style="width: 100%"/>
      </el-form-item>
      <el-form-item :label="$t('admin.content.collaboration.maxUses')">
        <el-input-number v-model="inviteForm.max_uses" :min="0" style="width: 100%"/>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="inviteFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
      <el-button :loading="inviteSaving" type="primary" @click="submitInvite">
        {{ $t('admin.common.save') }}
      </el-button>
    </template>
  </el-dialog>
</template>
