<script lang="ts" setup>
import {computed, onMounted, reactive, ref, watch} from 'vue'

import {ElMessage} from '@/utils/feedback'
import {pluginAction} from '@/utils/pluginAction'

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
  {key: 'pending', label: '待审批', icon: 'clock'},
  {key: 'my-requests', label: '我的申请', icon: 'circle-check'},
  {key: 'history', label: '统计概览', icon: 'clipboard-list'},
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
  {label: '待审批', value: stats.value.total_pending ?? '—'},
  {label: '已通过', value: stats.value.total_approved ?? '—'},
  {label: '已拒绝', value: stats.value.total_rejected ?? '—'},
  {label: '总计', value: stats.value.total ?? '—'},
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
    if (!result.success) error.value = result.error || '加载失败'
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
      ElMessage.success(dialog.action === 'approve' ? '已通过' : '已拒绝')
      dialog.open = false
      await loadCurrent()
    } else {
      ElMessage.error(result.error || '操作失败')
    }
  } finally {
    submitting.value = false
  }
}

function statusLabel(status?: string | null): string {
  if (status === 'approved') return '已通过'
  if (status === 'rejected') return '已拒绝'
  return '待审批'
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

      <EmptyState v-else-if="!items.length" description="有内容提交审批后会出现在这里" title="暂无数据"/>

      <el-table v-else :data="items" border>
        <el-table-column label="内容" min-width="260">
          <template #default="{row}">
            <p class="text-sm font-medium text-fg">{{ row.content_title || `#${row.content_id}` }}</p>
            <p class="text-xs text-fg-subtle">{{ row.content_type }} · {{ formatDate(row.created_at) }}</p>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="120">
          <template #default="{row}">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column align="right" label="操作" width="180">
          <template #default="{row}">
            <template v-if="tab === 'pending' && row.status === 'pending'">
              <el-button link type="success" @click="openDialog(row, 'approve')">通过</el-button>
              <el-button link type="danger" @click="openDialog(row, 'reject')">拒绝</el-button>
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
    <el-dialog v-model="dialog.open" :title="dialog.action === 'approve' ? '审批通过' : '拒绝'" width="440px">
      <el-input v-model="notes" :rows="3" placeholder="审批意见（可选）" type="textarea"/>
      <template #footer>
        <el-button @click="dialog.open = false">取消</el-button>
        <el-button :loading="submitting" :type="dialog.action === 'approve' ? 'success' : 'danger'"
                   @click="submitAction">
          确认
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
