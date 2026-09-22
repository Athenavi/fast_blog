<script lang="ts" setup>
import {computed, onMounted, ref, watch} from 'vue'

import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {pluginAction} from '@/utils/pluginAction'

const {t} = useI18n()

/**
 * Newsletter 管理（newsletter 插件后台页）
 *
 * 对应 `plugins/newsletter/frontend/admin/Page.tsx`：
 * 订阅者列表（分页）+ 三个统计数字 + 按需退订。
 * 原实现的 `AuthGuard` / `QueryProvider` / `AdminShell` 由宿主页与 admin 布局承担。
 */
interface Subscriber {
  id: number
  email: string
  name?: string | null
  source?: string | null
  is_active: boolean
  subscribed_at?: string | null
}

interface SubListResult {
  data: Subscriber[]
  total: number
}

interface Stats {
  total: number
  active: number
  unsubscribed: number
}

const PER_PAGE = 50

const page = ref(1)
const loading = ref(false)
const error = ref('')
const list = ref<Subscriber[]>([])
const total = ref(0)
const stats = ref<Stats>({total: 0, active: 0, unsubscribed: 0})
const unsubscribingId = ref<number | null>(null)

const pages = computed(() => Math.max(1, Math.ceil(total.value / PER_PAGE)))

async function loadStats(): Promise<void> {
  const result = await pluginAction<Stats>('newsletter', 'stats')
  stats.value = {
    total: result.data?.total ?? 0,
    active: result.data?.active ?? 0,
    unsubscribed: result.data?.unsubscribed ?? 0,
  }
}

async function loadList(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const result = await pluginAction<SubListResult>('newsletter', 'list_subscribers', {
      page: page.value,
      per_page: PER_PAGE,
    })
    list.value = result.data?.data ?? []
    total.value = result.data?.total ?? 0
    if (!result.success) error.value = result.error || t('admin.pluginPages.common.loadFailed')
  } finally {
    loading.value = false
  }
}

async function refresh(): Promise<void> {
  await Promise.all([loadList(), loadStats()])
}

async function unsubscribe(row: Subscriber): Promise<void> {
  await ElMessageBox.confirm(t('admin.pluginPages.newsletter.confirmUnsubscribe', {email: row.email}), t('admin.common.notice'), {type: 'warning'})
  unsubscribingId.value = row.id
  try {
    const result = await pluginAction('newsletter', 'admin_unsubscribe', {subscriber_id: row.id})
    if (result.success) {
      ElMessage.success(t('admin.pluginPages.newsletter.unsubscribed'))
      await refresh()
    } else {
      ElMessage.error(result.error || t('common.operationFailed'))
    }
  } finally {
    unsubscribingId.value = null
  }
}

function formatDate(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleDateString()
}

watch(page, loadList)
onMounted(refresh)
</script>

<template>
  <div class="p-4">
    <!-- 统计 -->
    <div class="mb-3 flex flex-wrap items-center justify-end gap-4 text-sm">
      <span class="flex items-center gap-1 text-fg-muted">
        <Icon class="h-4 w-4" name="user"/>
        {{ stats.total }} {{ t('admin.pluginPages.newsletter.total') }}
      </span>
      <span class="flex items-center gap-1 text-success">
        <Icon class="h-4 w-4" name="check"/>
        {{ stats.active }} {{ t('common.active') }}
      </span>
      <span class="flex items-center gap-1 text-fg-subtle">
        <Icon class="h-4 w-4" name="x"/>
        {{ stats.unsubscribed }} {{ t('admin.pluginPages.newsletter.unsubscribed') }}
      </span>
      <el-button :loading="loading" link type="primary" @click="refresh">
        <Icon class="mr-1 h-3.5 w-3.5" name="refresh-cw"/>
        {{ t('admin.common.refresh') }}
      </el-button>
    </div>

    <p v-if="error" class="mb-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

    <EmptyState
      v-if="!loading && !total"
      :description="t('admin.pluginPages.newsletter.emptyDesc')"
      :title="t('admin.pluginPages.newsletter.emptyTitle')"
    />

    <template v-else>
      <el-table v-loading="loading" :data="list" border>
        <el-table-column label="Email" min-width="220" prop="email"/>
        <el-table-column :label="t('admin.common.name')" min-width="140">
          <template #default="{row}">{{ row.name || '-' }}</template>
        </el-table-column>
        <el-table-column :label="t('admin.pluginPages.newsletter.source')" min-width="120">
          <template #default="{row}">{{ row.source || '-' }}</template>
        </el-table-column>
        <el-table-column :label="t('admin.pluginPages.newsletter.subscribedAt')" width="140">
          <template #default="{row}">{{ formatDate(row.subscribed_at) }}</template>
        </el-table-column>
        <el-table-column :label="t('admin.common.status')" align="center" width="110">
          <template #default="{row}">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? t('common.active') : t('admin.pluginPages.newsletter.unsubscribed') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('admin.common.actions')" align="right" width="110">
          <template #default="{row}">
            <el-button
              v-if="row.is_active"
              :loading="unsubscribingId === row.id"
              link
              type="danger"
              @click="unsubscribe(row)"
            >{{ t('admin.pluginPages.newsletter.unsubscribe') }}
            </el-button>
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
  </div>
</template>
