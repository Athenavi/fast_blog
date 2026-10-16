<script lang="ts" setup>
import {computed, onMounted, reactive, ref, watch} from 'vue'

import {ElMessage} from '@/utils/feedback'
import {pluginAction} from '@/utils/pluginAction'

const {t} = useI18n()

/**
 * 内容审批（approval 插件后台页）
 *
 * 对应 `plugins/approval/frontend/admin/Page.tsx`：
 * 三个页签（待审批 / 我的申请 / 统计概览）+ 审批动作弹窗（可填审批意见）。
 */
interface ApprovalItem {
  id: number
  content_id?: number | null
  content_title?: string | null
  content_type?: string | null
  status?: string | null
  created_at?: string | null
}

interface ListResult {
  items: ApprovalItem[]
  total: number
}

interface Stats {
  total_pending?: number
  total_approved?: number
  total_rejected?: number
  total?: number
}

type TabKey = 'pending' | 'my-requests' | 'history'

const TABS: Array<{ key: TabKey; label: string; icon: string }> = [
  {key: 'pending', label: t('admin.pluginPages.approval.tabs.pending'), icon: 'clock'},
  {key: 'my-requests', label: t('admin.pluginPages.approval.tabs.myRequests'), icon: 'circle-check'},
  {key: 'history', label: t('admin.pluginPages.approval.tabs.stats'), icon: 'clipboard-list'},
]

const PER_PAGE = 15

const tab = ref<TabKey>('pending')
const page = ref(1)
const loading = ref(false)
const error = ref('')

const items = ref<ApprovalItem[]>([])
const total = ref(0)
const stats = ref<Stats>({})

const dialog = reactive<{ open: boolean; id: number; action: 'approve' | 'reject' }>({
  open: false,
  id: 0,
  action: 'approve',
})
const notes = ref('')
const submitting = ref(false)

const statCards = computed(() => [
  {label: t('admin.pluginPages.approval.stats.pending'), value: stats.value.total_pending ?? '—'},
  {label: t('admin.pluginPages.approval.stats.approved'), value: stats.value.total_approved ?? '—'},
  {label: t('admin.pluginPages.approval.stats.rejected'), value: stats.value.total_rejected ?? '—'},
  {label: t('admin.pluginPages.approval.stats.total'), value: stats.value.total ?? '—'},
])

async function loadCurrent(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    if (tab.value === 'history') {
      const result = await pluginAction<Stats>('approval', 'get_stats')
      stats.value = result.data ?? {}
      return
    }

    const action = tab.value === 'pending' ? 'list_pending' : 'list_my_requests'
    const result = await pluginAction<ListResult>('approval', action, {page: page.value, per_page: PER_PAGE})
    items.value = result.data?.items ?? []
    total.value = result.data?.total ?? 0
    if (!result.success) error.value = result.error || t('admin.pluginPages.common.loadFailed')
  } finally {
    loading.value = false
  }
}

function switchTab(key: TabKey): void {
  tab.value = key
  page.value = 1
}

function openDialog(item: ApprovalItem, action: 'approve' | 'reject'): void {
  dialog.open = true
  dialog.id = item.id
  dialog.action = action
  notes.value = ''
}

async function submitAction(): Promise<void> {
  submitting.value = true
  try {
    const result = await pluginAction('approval', dialog.action, {
      record_id: dialog.id,
      notes: notes.value,
    })
    if (result.success) {
      ElMessage.success(dialog.action === 'approve' ? t('common.approved') : t('common.rejected'))
      dialog.open = false
      await loadCurrent()
    } else {
      ElMessage.error(result.error || t('common.operationFailed'))
    }
  } finally {
    submitting.value = false
  }
}

function statusLabel(status?: string | null): string {
  if (status === 'approved') return t('common.approved')
  if (status === 'rejected') return t('common.rejected')
  return t('common.pending')
}

function statusTagType(status?: string | null): 'success' | 'danger' | 'warning' {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  return 'warning'
}

function formatDate(value?: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString()
}

watch(page, loadCurrent)
onMounted(loadCurrent)
</script>

<template>
  <div class="p-4">
    <!-- 页签 -->
    <div class="mb-4 flex flex-wrap gap-2">
      <button
        v-for="item in TABS"
        :key="item.key"
        :class="
          tab === item.key
            ? 'bg-primary text-primary-fg'
            : 'border border-line bg-surface text-fg-muted hover:bg-surface-soft'
        "
        class="flex items-center gap-1.5 rounded-control px-4 py-2 text-sm font-medium transition-colors"
        type="button"
        @click="switchTab(item.key)"
      >
        <Icon :name="item.icon" class="h-4 w-4"/>
        {{ item.label }}
      </button>
    </div>

    <p v-if="error" class="mb-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

    <!-- 统计概览 -->
    <div v-if="tab === 'history'" class="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
      <div v-for="card in statCards" :key="card.label" class="rounded-card border border-line bg-surface p-4">
        <p class="mb-1 text-xs text-fg-muted">{{ card.label }}</p>
        <p class="text-2xl font-bold text-fg">{{ card.value }}</p>
      </div>
    </div>

    <!-- 列表 -->
    <template v-else>
      <div v-if="loading" class="space-y-3">
        <Skeleton v-for="i in 5" :key="i" class="h-16 w-full"/>
      </div>

      <EmptyState v-else-if="!items.length" :description="t('admin.pluginPages.approval.emptyDesc')"
                  :title="t('admin.common.empty')"/>

      <el-table v-else :data="items" border>
        <el-table-column :label="t('admin.pluginPages.approval.content')" min-width="260">
          <template #default="{row}">
            <p class="text-sm font-medium text-fg">{{ row.content_title || `#${row.content_id}` }}</p>
            <p class="text-xs text-fg-subtle">{{ row.content_type }} · {{ formatDate(row.created_at) }}</p>
          </template>
        </el-table-column>

        <el-table-column :label="t('admin.common.status')" width="120">
          <template #default="{row}">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="t('admin.common.actions')" align="right" width="180">
          <template #default="{row}">
            <template v-if="tab === 'pending' && row.status === 'pending'">
              <el-button link type="success" @click="openDialog(row, 'approve')">{{ t('common.approved') }}</el-button>
              <el-button link type="danger" @click="openDialog(row, 'reject')">{{ t('common.rejected') }}</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > PER_PAGE"
        v-model:current-page="page"
        :page-size="PER_PAGE"
        :total="total"
        class="mt-3 justify-end"
        layout="total, prev, pager, next"
      />
    </template>

    <!-- 审批弹窗 -->
    <el-dialog v-model="dialog.open"
               :title="dialog.action === 'approve' ? t('admin.pluginPages.approval.dialogApproveTitle') : t('common.rejected')"
               width="440px">
      <el-input v-model="notes" :placeholder="t('admin.pluginPages.approval.notesPlaceholder')" :rows="3"
                type="textarea"/>
      <template #footer>
        <el-button @click="dialog.open = false">{{ t('admin.common.cancel') }}</el-button>
        <el-button :loading="submitting" :type="dialog.action === 'approve' ? 'success' : 'danger'"
                   @click="submitAction">
          {{ t('common.confirm') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
