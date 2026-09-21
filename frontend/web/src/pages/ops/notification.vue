<script lang="ts" setup>
const {t} = useI18n()
/**
 * 站内通知
 *
 * 对齐 v3 `/ops/notification`：列表（可只看未读）、未读数、标记已读、
 * 全部已读、删除单条、清理已读。所有接口都以「当前用户」为 recipient。
 *
 * 样式统一使用 Element Plus 的 CSS 变量，避免写死色值。
 */
import {Delete, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {reactive, ref} from 'vue'

import {notificationApi, type NotificationItem} from '@/api'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ops.notification.notifications',
  permission: 'module_ops:notification:view',
})

const loading = ref(false)
const list = ref<NotificationItem[]>([])
const total = ref(0)
const unread = ref(0)
const unreadOnly = ref(false)

const query = reactive({page: 1, page_size: 20})

async function loadList(): Promise<void> {
  loading.value = true
  try {
    const data = await notificationApi.list({
      page: query.page,
      page_size: query.page_size,
      ...(unreadOnly.value ? {unread_only: true} : {}),
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadUnread(): Promise<void> {
  try {
    const data = await notificationApi.unreadCount()
    unread.value = data.unread
  } catch {
    unread.value = 0
  }
}

function onFilterChange(): void {
  query.page = 1
  loadList()
}

async function refresh(): Promise<void> {
  await Promise.all([loadList(), loadUnread()])
}

// ---------------------------------------------------------------- 操作
async function markRead(row: NotificationItem): Promise<void> {
  if (row.is_read) return
  await notificationApi.markRead(row.id)
  row.is_read = true
  row.read_at = new Date().toISOString()
  await loadUnread()
}

// ---------------------------------------------------------------- 多选与批量
const selectedIds = ref<number[]>([])

function onSelectionChange(rows: NotificationItem[]): void {
  selectedIds.value = rows.map((row) => row.id)
}

function clearSelection(): void {
  selectedIds.value = []
}

async function batchRead(): Promise<void> {
  if (!selectedIds.value.length) return
  const result = await notificationApi.batchRead([...selectedIds.value])
  ElMessage.success(t('admin.common.batchDone', {n: result.affected}))
  clearSelection()
  await refresh()
}

async function batchDelete(): Promise<void> {
  if (!selectedIds.value.length) return
  await ElMessageBox.confirm(
    t('admin.ops.notification.deleteSelectedConfirm', {n: selectedIds.value.length}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  const result = await notificationApi.batchDelete([...selectedIds.value])
  ElMessage.success(t('admin.common.batchDone', {n: result.affected}))
  clearSelection()
  await refresh()
}

async function readAll(): Promise<void> {
  const result = await notificationApi.readAll()
  ElMessage.success(t('admin.ops.notification.markedRead', {n: result?.affected ?? 0}))
  await refresh()
}

async function removeRow(row: NotificationItem): Promise<void> {
  await ElMessageBox.confirm(t('admin.ops.notification.deleteConfirm', {name: row.title || row.id}), t('admin.common.notice'), {type: 'warning'})
  await notificationApi.remove(row.id)
  ElMessage.success(t('admin.ops.notification.deleted'))
  await refresh()
}

async function cleanRead(): Promise<void> {
  await ElMessageBox.confirm(t('admin.ops.notification.clearAllReadNotificationsThisActionCannotBeUndone'), t('admin.common.notice'), {type: 'warning'})
  const result = await notificationApi.clean()
  ElMessage.success(t('admin.ops.notification.cleaned', {n: result?.affected ?? 0}))
  await refresh()
}

function typeTag(type?: string | null): 'primary' | 'success' | 'warning' | 'danger' | 'info' {
  if (type === 'error' || type === 'danger') return 'danger'
  if (type === 'warning') return 'warning'
  if (type === 'success') return 'success'
  return 'info'
}

onMounted(refresh)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="toolbar">
        <el-badge :hidden="unread === 0" :value="unread" class="badge">
          <el-button :icon="Refresh" @click="refresh">{{ $t('admin.common.refresh') }}</el-button>
        </el-badge>

        <el-switch
          v-model="unreadOnly"
          :active-text="$t('admin.ops.notification.unreadOnly')"
          inline-prompt
          @change="onFilterChange"
        />

        <div class="spacer"/>

        <el-button v-auth="'module_ops:notification:edit'" @click="readAll">
          {{ $t('admin.ops.notification.markAllAsRead') }}
        </el-button>
        <el-button v-auth="'module_ops:notification:edit'" :icon="Delete" plain type="danger" @click="cleanRead">
          {{ $t('admin.ops.notification.cleanRead') }}
        </el-button>
      </div>

      <AdminSelectionBar :count="selectedIds.length" @clear="clearSelection">
        <el-button v-auth="'module_ops:notification:edit'" plain type="primary" @click="batchRead">
          {{ $t('admin.ops.notification.batchRead') }}
        </el-button>
        <el-button v-auth="'module_ops:notification:edit'" plain type="danger" @click="batchDelete">
          {{ $t('admin.common.delete') }}
        </el-button>
      </AdminSelectionBar>

      <AdminTableSkeleton v-if="loading && !list.length" :rows="5"/>
      <AdminEmpty v-else-if="!loading && !list.length" :title="$t('admin.common.empty')"/>
      <el-table v-else v-loading="loading" :data="list" row-key="id" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="46"/>
        <el-table-column label="ID" prop="id" width="80"/>
        <el-table-column :label="$t('admin.cache.level')" width="100">
          <template #default="{row}">
            <el-tag :type="typeTag(row.type)" size="small">{{
                row.type || t('admin.ops.notification.notifications')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.menu.itemTitle')" min-width="200">
          <template #default="{row}">
            <span :class="row.is_read ? 'read' : 'unread'">{{ row.title || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('article.content')" min-width="300" prop="message" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.common.status')" width="90">
          <template #default="{row}">
            <el-tag :type="row.is_read ? 'info' : 'primary'" size="small">
              {{ row.is_read ? t('admin.ops.notification.read') : t('admin.ops.notification.unread') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.log.time')" width="170">
          <template #default="{row}">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="160">
          <template #default="{row}">
            <el-button v-if="!row.is_read" link type="primary" @click="markRead(row)">
              {{ $t('admin.ops.notification.markAsRead') }}
            </el-button>
            <el-button
              v-auth="'module_ops:notification:edit'"
              :icon="Delete"
              link
              type="danger"
              @click="removeRow(row)"
            >
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :page-sizes="[20, 50, 100]"
        :total="total"
        class="pagination"
        layout="total, sizes, prev, pager, next"
        @current-change="loadList"
        @size-change="onFilterChange"
      />
    </el-card>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.badge {
  margin-right: 8px;
}

.spacer {
  flex: 1;
}

.read {
  color: var(--el-text-color-secondary);
}

.unread {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.pagination {
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
