<script lang="ts" setup>
/**
 * 协作管理 · 协同文档（yjs）面板
 *
 * 从 `pages/content/collaboration.vue` 的「协同文档（yjs）」标签页抽出。它是本页最大的
 * 一块：房间只读视图 / 访问权自检 / 协作者 / 版本历史与回滚 / 正文快照。
 *
 * 与页面之间只有 `active` 一个属性 —— 对应原 `onTabChange` 里"切到 yjs 标签时拉一次
 * 房间列表"。其余状态（当前文档 id、邀请码、各块加载标记、版本分页）全部自包含，
 * 不与其它标签页共享。
 */
import {Document, Refresh, Upload} from '@element-plus/icons-vue'
import {reactive, ref, watch} from 'vue'

import {
  yjsApi,
  type YjsCollaborators,
  type YjsDocumentAccess,
  type YjsInviteCollaborator,
  type YjsRevision,
  type YjsRevisionDetail,
  type YjsRoomDetail,
  type YjsRoomItem,
} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

const props = defineProps<{
  /** 本标签页是否激活 —— 原页面在 `onTabChange` 里切到 yjs 时才拉房间列表 */
  active: boolean
}>()

const {t} = useI18n()

/** 输入框中的文档 ID（= 文章 ID） */
const yjsDocumentId = ref<number | undefined>(undefined)
/** 非作者时可填的协作邀请码（view 码只读，edit 码可写） */
const yjsInviteCode = ref('')
/** 已加载的文档 ID：翻页 / 回滚 / 快照都固定用它，避免读输入框的中间值 */
const yjsActiveDocumentId = ref<number | null>(null)

/** 本进程活跃房间列表 */
const yjsRooms = ref<YjsRoomItem[]>([])
/** 房间口径说明（仅本进程，跨 worker 状态在 Redis） */
const yjsRoomsScope = ref('')
const yjsRoomsLoading = ref(false)

const yjsRoomDetail = ref<YjsRoomDetail | null>(null)
const yjsRoomDetailLoading = ref(false)

const yjsAccess = ref<YjsDocumentAccess | null>(null)
const yjsAccessLoading = ref(false)

const yjsCollaborators = ref<YjsCollaborators | null>(null)
const yjsCollaboratorsLoading = ref(false)

const yjsVersionDetail = ref<YjsRevisionDetail | null>(null)
const yjsVersionDetailVisible = ref(false)
const yjsVersionDetailLoading = ref(false)

const snapshotForm = reactive({html: '', change_summary: '', force: false})
const snapshotSaving = ref(false)
const restoreSaving = ref(false)

/** 当前请求应带的邀请码（空串按未填处理） */
function currentInvite(): string | null {
  return yjsInviteCode.value.trim() || null
}

async function loadYjsRooms(): Promise<void> {
  yjsRoomsLoading.value = true
  try {
    const result = await yjsApi.listRooms()
    yjsRooms.value = result.rooms ?? []
    yjsRoomsScope.value = result.scope || ''
  } finally {
    yjsRoomsLoading.value = false
  }
}

async function loadYjsRoomDetail(): Promise<void> {
  if (yjsActiveDocumentId.value === null) return
  yjsRoomDetailLoading.value = true
  try {
    yjsRoomDetail.value = await yjsApi.getRoom(yjsActiveDocumentId.value, currentInvite())
  } finally {
    yjsRoomDetailLoading.value = false
  }
}

async function loadYjsAccess(): Promise<void> {
  if (yjsActiveDocumentId.value === null) return
  yjsAccessLoading.value = true
  try {
    yjsAccess.value = await yjsApi.getAccess(yjsActiveDocumentId.value, currentInvite())
  } finally {
    yjsAccessLoading.value = false
  }
}

async function loadYjsCollaborators(): Promise<void> {
  if (yjsActiveDocumentId.value === null) return
  yjsCollaboratorsLoading.value = true
  try {
    yjsCollaborators.value = await yjsApi.listCollaborators(
      yjsActiveDocumentId.value,
      currentInvite(),
    )
  } finally {
    yjsCollaboratorsLoading.value = false
  }
}

/** 版本历史分页（真表 `article_revisions`，不含正文） */
const versionState = useAdminList<YjsRevision, PageQuery & { invite?: string }>({
  fetcher: (params) => {
    const invite = currentInvite()
    return yjsApi.listVersions(
      yjsActiveDocumentId.value ?? 0,
      invite ? {...params, invite} : params,
    )
  },
  defaultQuery: {},
  syncUrl: false,
  immediate: false,
})

const versionList = versionState.rows
const versionLoading = versionState.loading
const versionTotal = versionState.total
const versionPage = versionState.page
const versionPageSize = versionState.pageSize
const versionLoad = versionState.reload
const onVersionPageChange = versionState.onPageChange
const onVersionSizeChange = versionState.onSizeChange

/** 拉取指定文档的房间详情 / 访问权 / 协作者 / 版本历史 */
function yjsLoadAll(): void {
  loadYjsRoomDetail().catch(() => undefined)
  loadYjsAccess().catch(() => undefined)
  loadYjsCollaborators().catch(() => undefined)
  versionState.search().catch(() => undefined)
}

/** 用输入框中的文档 ID 加载 */
function applyDocumentId(): void {
  if (yjsDocumentId.value === undefined) {
    ElMessage.warning(t('admin.content.collaboration.documentIdRequired'))
    return
  }
  yjsActiveDocumentId.value = yjsDocumentId.value
  yjsLoadAll()
}

/** 点击房间行：直接加载该文档 */
function loadRoomById(id: number): void {
  yjsDocumentId.value = id
  yjsActiveDocumentId.value = id
  yjsLoadAll()
}

/** 查看单个版本详情（含正文） */
async function openVersionDetail(row: YjsRevision): Promise<void> {
  if (yjsActiveDocumentId.value === null || row.revision_number === null) return
  yjsVersionDetail.value = null
  yjsVersionDetailVisible.value = true
  yjsVersionDetailLoading.value = true
  try {
    yjsVersionDetail.value = await yjsApi.getVersion(
      yjsActiveDocumentId.value,
      row.revision_number,
      currentInvite(),
    )
  } finally {
    yjsVersionDetailLoading.value = false
  }
}

/** 保存正文快照（saved=false 表示去重跳过，不是失败） */
async function submitSnapshot(): Promise<void> {
  if (yjsActiveDocumentId.value === null || !snapshotForm.html.trim()) {
    ElMessage.warning(t('admin.content.collaboration.htmlRequired'))
    return
  }
  snapshotSaving.value = true
  try {
    const result = await yjsApi.saveSnapshot(
      yjsActiveDocumentId.value,
      {
        html: snapshotForm.html,
        change_summary: snapshotForm.change_summary.trim() || null,
        force: snapshotForm.force,
      },
      currentInvite(),
    )
    ElMessage.success(
      result.saved
        ? t('admin.content.collaboration.snapshotSaved', {n: result.revision_number ?? '-'})
        : t('admin.content.collaboration.snapshotSkipped'),
    )
    if (result.saved) {
      Object.assign(snapshotForm, {html: '', change_summary: '', force: false})
    }
    await versionLoad()
    await loadYjsRoomDetail()
  } finally {
    snapshotSaving.value = false
  }
}

/** 回滚到历史版本（历史不被改写，会追加一条新修订） */
async function onRestoreVersion(row: YjsRevision): Promise<void> {
  if (yjsActiveDocumentId.value === null || row.revision_number === null) return
  await ElMessageBox.confirm(
    t('admin.content.collaboration.restoreConfirm', {n: row.revision_number}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  restoreSaving.value = true
  try {
    const result = await yjsApi.restoreVersion(
      yjsActiveDocumentId.value,
      row.revision_number,
      {change_summary: null},
      currentInvite(),
    )
    ElMessage.success(t('admin.content.collaboration.restored', {n: result.new_revision_number}))
    await versionLoad()
    await loadYjsRoomDetail()
  } finally {
    restoreSaving.value = false
  }
}

// 对应原 `onTabChange` 里切到 yjs 标签时做的事（immediate 覆盖"直接落在这个标签"的情况）
watch(
  () => props.active,
  (isActive) => {
    if (isActive) loadYjsRooms().catch(() => undefined)
  },
  {immediate: true},
)
</script>

<template>
  <el-card class="mb-3" shadow="never">
    <el-form :inline="true">
      <el-form-item :label="$t('admin.content.collaboration.documentId')">
        <el-input-number v-model="yjsDocumentId" :min="1" style="width: 160px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.content.collaboration.inviteCodeOptional')">
        <el-input v-model="yjsInviteCode" :placeholder="$t('admin.content.collaboration.inviteOptionalPlaceholder')"
                  clearable
                  style="width: 240px"/>
      </el-form-item>
      <el-form-item>
        <el-button :icon="Document" type="primary" @click="applyDocumentId">
          {{ $t('admin.content.collaboration.loadDocument') }}
        </el-button>
        <el-button :icon="Refresh" @click="loadYjsRooms()">
          {{ $t('admin.content.collaboration.refreshRooms') }}
        </el-button>
      </el-form-item>
    </el-form>
  </el-card>

  <el-card class="mb-3" shadow="never">
    <div class="table-toolbar">
      <span class="table-toolbar__title">{{ $t('admin.content.collaboration.activeRooms') }}</span>
      <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: yjsRooms.length}) }}</span>
    </div>
    <el-alert v-if="yjsRoomsScope" :closable="false" :title="yjsRoomsScope" class="mb-3"
              show-icon type="info"/>
    <el-table v-loading="yjsRoomsLoading" :data="yjsRooms" border size="small" stripe>
      <el-table-column :label="$t('admin.content.collaboration.documentId')" prop="document_id"
                       width="120"/>
      <el-table-column :label="$t('admin.content.collaboration.onlineClients')" prop="clients"
                       width="130"/>
      <el-table-column :label="$t('admin.content.collaboration.roomState')" width="140">
        <template #default="{ row }">
          <el-tag
            :type="(row as YjsRoomItem).state === 'crowded' ? 'warning' : (row as YjsRoomItem).active ? 'success' : 'info'"
            size="small">
            {{ (row as YjsRoomItem).state }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="140">
        <template #default="{ row }">
          <el-button link type="primary"
                     @click="loadRoomById((row as YjsRoomItem).document_id)">
            {{ $t('admin.content.collaboration.loadDocument') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-card v-if="yjsActiveDocumentId !== null" class="mb-3" shadow="never">
    <div class="table-toolbar">
      <span class="table-toolbar__title">{{ $t('admin.content.collaboration.roomDetailTitle') }}</span>
      <span class="table-toolbar__total">
        #{{ yjsActiveDocumentId }}
      </span>
    </div>
    <el-descriptions v-loading="yjsRoomDetailLoading" :column="2" border size="small">
      <el-descriptions-item :label="$t('admin.content.collaboration.onlineClients')">
        {{ yjsRoomDetail?.clients ?? '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.content.collaboration.roomState')">
        {{ yjsRoomDetail?.state ?? '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.content.collaboration.revisionCount')">
        {{ yjsRoomDetail?.revision_count ?? '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.content.collaboration.latestRevision')">
        {{ yjsRoomDetail?.latest_revision_number ?? '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.content.collaboration.latestRevisionAt')">
        {{ yjsRoomDetail?.latest_revision_at ?? '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.content.collaboration.contentChars')">
        {{ yjsRoomDetail?.content_chars ?? '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.content.collaboration.hasContent')">
        {{ yjsRoomDetail?.has_content ? $t('admin.common.yes') : $t('admin.common.no') }}
      </el-descriptions-item>
    </el-descriptions>

    <el-divider/>
    <div class="table-toolbar">
      <span class="table-toolbar__title">{{ $t('admin.content.collaboration.accessTitle') }}</span>
    </div>
    <el-descriptions v-loading="yjsAccessLoading" :column="2" border size="small">
      <el-descriptions-item :label="$t('admin.content.collaboration.docTitle')">
        {{ yjsAccess?.title ?? '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.content.collaboration.isAuthor')">
        {{ yjsAccess?.is_author ? $t('admin.common.yes') : $t('admin.common.no') }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.content.collaboration.allowed')">
        {{ yjsAccess?.allowed ? $t('admin.common.yes') : $t('admin.common.no') }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.content.collaboration.canEdit')">
        {{ yjsAccess?.can_edit ? $t('admin.common.yes') : $t('admin.common.no') }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.content.collaboration.via')">
        {{ yjsAccess?.via ?? '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.content.collaboration.permission')">
        {{ yjsAccess?.permission ?? '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.content.collaboration.accessReason')" :span="2">
        {{ yjsAccess?.reason ?? '-' }}
      </el-descriptions-item>
    </el-descriptions>

    <el-divider/>
    <div class="table-toolbar">
      <span class="table-toolbar__title">
        {{ $t('admin.content.collaboration.collaborators') }}
      </span>
      <span class="table-toolbar__total">
        {{ $t('admin.content.collaboration.inviteCount') }}: {{ yjsCollaborators?.invite_count ?? 0 }}
      </span>
    </div>
    <el-table v-loading="yjsCollaboratorsLoading" :data="yjsCollaborators?.invites ?? []"
              border size="small" stripe>
      <el-table-column :label="$t('admin.content.collaboration.inviteCode')" min-width="200"
                       show-overflow-tooltip>
        <template #default="{ row }">
          {{ (row as YjsInviteCollaborator).invite_code || '-' }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.content.collaboration.permission')" prop="permission"
                       width="100"/>
      <el-table-column :label="$t('admin.content.collaboration.creatorId')" prop="creator_id"
                       width="110"/>
      <el-table-column :label="$t('admin.content.collaboration.usage')" align="center" width="110">
        <template #default="{ row }">
          {{ (row as YjsInviteCollaborator).use_count }}/{{ (row as YjsInviteCollaborator).max_uses || '∞' }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.content.collaboration.expiresAt')" min-width="170"
                       prop="expires_at"/>
      <el-table-column :label="$t('admin.content.collaboration.usable')" align="center" width="100">
        <template #default="{ row }">
          <el-tag :type="(row as YjsInviteCollaborator).usable ? 'success' : 'info'" size="small">
            {{ (row as YjsInviteCollaborator).usable ? $t('admin.common.yes') : $t('admin.common.no') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.content.collaboration.canEdit')" align="center" width="100">
        <template #default="{ row }">
          <el-tag :type="(row as YjsInviteCollaborator).can_edit ? 'success' : 'info'" size="small">
            {{ (row as YjsInviteCollaborator).can_edit ? $t('admin.common.yes') : $t('admin.common.no') }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-divider/>
    <div class="table-toolbar">
      <span class="table-toolbar__title">{{ $t('admin.content.collaboration.snapshotTitle') }}</span>
    </div>
    <el-form :model="snapshotForm" label-width="130px">
      <el-form-item :label="$t('admin.content.collaboration.snapshotHtml')" required>
        <el-input v-model="snapshotForm.html" :autosize="{minRows: 4, maxRows: 12}" type="textarea"/>
      </el-form-item>
      <el-form-item :label="$t('admin.content.collaboration.changeSummary')">
        <el-input v-model="snapshotForm.change_summary" maxlength="255"/>
      </el-form-item>
      <el-form-item :label="$t('admin.content.collaboration.force')">
        <el-switch v-model="snapshotForm.force"/>
        <span class="hint">{{ $t('admin.content.collaboration.forceHint') }}</span>
      </el-form-item>
      <el-form-item>
        <el-button v-auth="'module_content:collaboration:edit'" :icon="Upload"
                   :loading="snapshotSaving" type="primary" @click="submitSnapshot">
          {{ $t('admin.content.collaboration.saveSnapshot') }}
        </el-button>
      </el-form-item>
    </el-form>
  </el-card>

  <el-card v-if="yjsActiveDocumentId !== null" shadow="never">
    <div class="table-toolbar">
      <span class="table-toolbar__title">{{ $t('admin.content.collaboration.versionHistory') }}</span>
      <el-button :icon="Refresh" size="small" @click="versionLoad()">
        {{ $t('admin.common.refresh') }}
      </el-button>
    </div>
    <el-table v-loading="versionLoading" :data="versionList" border size="small" stripe>
      <el-table-column :label="$t('admin.content.collaboration.revisionNumber')"
                       prop="revision_number" width="100"/>
      <el-table-column :label="$t('admin.content.collaboration.title')" min-width="160" prop="title"
                       show-overflow-tooltip/>
      <el-table-column :label="$t('admin.content.collaboration.author')" min-width="140"
                       prop="author_name"/>
      <el-table-column :label="$t('admin.content.collaboration.changeSummary')" min-width="180"
                       prop="change_summary" show-overflow-tooltip/>
      <el-table-column :label="$t('admin.content.collaboration.contentChars')" prop="content_chars"
                       width="120"/>
      <el-table-column :label="$t('admin.content.collaboration.createdAt')" min-width="170"
                       prop="created_at"/>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="170">
        <template #default="{ row }">
          <el-button link type="primary" @click="openVersionDetail(row as YjsRevision)">
            {{ $t('admin.content.collaboration.viewVersion') }}
          </el-button>
          <el-button v-auth="'module_content:collaboration:edit'" :loading="restoreSaving"
                     link type="warning" @click="onRestoreVersion(row as YjsRevision)">
            {{ $t('admin.content.collaboration.restore') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination :current-page="versionPage" :page-size="versionPageSize"
                   :page-sizes="[10, 20, 50, 100]" :total="versionTotal" background
                   class="table-pagination" layout="total, sizes, prev, pager, next"
                   @current-change="onVersionPageChange" @size-change="onVersionSizeChange"/>
  </el-card>

  <!-- 版本详情 -->
  <el-dialog v-model="yjsVersionDetailVisible"
             :title="$t('admin.content.collaboration.versionDetailTitle')" width="720px">
    <div v-loading="yjsVersionDetailLoading">
      <el-alert v-if="yjsVersionDetail?.content_is_truncated" :closable="false"
                :title="$t('admin.content.collaboration.contentTruncated')"
                class="mb-3" show-icon type="warning"/>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item :label="$t('admin.content.collaboration.revisionNumber')">
          {{ yjsVersionDetail?.revision_number ?? '-' }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.content.collaboration.author')">
          {{ yjsVersionDetail?.author_name || yjsVersionDetail?.author_id || '-' }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.content.collaboration.changeSummary')" :span="2">
          {{ yjsVersionDetail?.change_summary || '-' }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.content.collaboration.contentChars')">
          {{ yjsVersionDetail?.content_chars ?? '-' }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.content.collaboration.hashCode')">
          {{ yjsVersionDetail?.hash_code || '-' }}
        </el-descriptions-item>
      </el-descriptions>
      <el-divider/>
      <pre class="yjs-content">{{ yjsVersionDetail?.content || '' }}</pre>
    </div>
    <template #footer>
      <el-button @click="yjsVersionDetailVisible = false">{{ $t('admin.common.cancel') }}</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
/* 这几个类来自 styles/admin.css（全局）与页面原先的 scoped 覆盖，随本面板一起搬过来 */
.mb-3 {
  margin-bottom: 12px;
}

.hint {
  margin-left: 12px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.yjs-content {
  max-height: 360px;
  margin: 0;
  padding: 12px;
  overflow: auto;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
