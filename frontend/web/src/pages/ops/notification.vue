<script lang="ts" setup>
const {t} = useI18n()
/**
 * 站内通知
 *
 * 对齐 v3 `/ops/notification`：列表（可只看未读）、未读数、标记已读、
 * 全部已读、删除单条、清理已读，以及批量标记已读 / 批量删除。
 * 所有接口都以「当前用户」为 recipient（服务层强制）。
 *
 * 多选与批量条由 `AdminListShell` 提供，这里只需实现批量动作本身。
 */
import {Delete, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, ref} from 'vue'

import {notificationApi, type NotificationItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ops.notification.notifications',
  permission: 'module_ops:notification:view',
})

interface NotificationQueryForm extends PageQuery {
  unread_only?: boolean
}

const list = useAdminList<NotificationItem, NotificationQueryForm>({
  fetcher: (params) => notificationApi.list(params),
  defaultQuery: {unread_only: undefined},
  syncUrl: true,
})

/** 只看未读：关掉时从请求里移除该字段（而不是传 false） */
const unreadOnly = computed({
  get: () => list.query.unread_only === true,
  set: (value: boolean) => {
    list.query.unread_only = value ? true : undefined
  },
})

const unread = ref(0)

async function loadUnread(): Promise<void> {
  try {
    const data = await notificationApi.unreadCount()
    unread.value = data.unread
  } catch {
    unread.value = 0
  }
}

/** 列表 + 未读数一起刷新（未读数变化会影响工具条徽标） */
async function refresh(): Promise<void> {
  await Promise.all([list.reload(), loadUnread()])
}

// ---------------------------------------------------------------- 操作
async function markRead(row: NotificationItem): Promise<void> {
  if (row.is_read) return
  await notificationApi.markRead(row.id)
  row.is_read = true
  row.read_at = new Date().toISOString()
  await loadUnread()
}

async function batchRead(): Promise<void> {
  if (!list.selectedIds.value.length) return
  const result = await notificationApi.batchRead([...list.selectedIds.value])
  ElMessage.success(t('admin.common.batchDone', {n: result.affected}))
  list.clearSelection()
  await refresh()
}

async function batchDelete(): Promise<void> {
  if (!list.selectedIds.value.length) return
  await ElMessageBox.confirm(
    t('admin.ops.notification.deleteSelectedConfirm', {n: list.selectedIds.value.length}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  const result = await notificationApi.batchDelete([...list.selectedIds.value])
  ElMessage.success(t('admin.common.batchDone', {n: result.affected}))
  list.clearSelection()
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
  <AdminPage :desc="$t('admin.ops.notification.desc')" :title="$t('admin.ops.notification.notifications')">
    <template #actions>
      <el-badge :hidden="unread === 0" :value="unread" class="mr-2">
        <el-button :icon="Refresh" @click="refresh">{{ $t('admin.common.refresh') }}</el-button>
      </el-badge>

      <el-button v-auth="'module_ops:notification:edit'" @click="readAll">
        {{ $t('admin.ops.notification.markAllAsRead') }}
      </el-button>
      <el-button v-auth="'module_ops:notification:edit'" :icon="Delete" plain type="danger" @click="cleanRead">
        {{ $t('admin.ops.notification.cleanRead') }}
      </el-button>
    </template>

    <AdminListShell
      :empty-desc="list.hasFilters.value
        ? $t('admin.ops.notification.emptyFiltered')
        : $t('admin.ops.notification.emptyDesc')"
      :empty-title="$t('admin.ops.notification.emptyTitle')"
      :failed="list.failed.value"
      :loading="list.loading.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      :page-sizes="[20, 50, 100]"
      :rows="list.rows.value"
      :selection-count="list.selectedCount.value"
      :total="list.total.value"
      @refresh="refresh"
      @reset="list.reset"
      @search="list.search"
      @clear-selection="list.clearSelection"
      @page-change="list.onPageChange"
      @selection-change="list.onSelectionChange"
      @size-change="list.onSizeChange"
    >
      <template #filters>
        <el-form-item :label="$t('admin.ops.notification.unreadOnly')">
          <el-switch v-model="unreadOnly" @change="list.search()"/>
        </el-form-item>
      </template>

      <template #bulk>
        <el-button v-auth="'module_ops:notification:edit'" plain type="primary" @click="batchRead">
          {{ $t('admin.ops.notification.batchRead') }}
        </el-button>
        <el-button v-auth="'module_ops:notification:edit'" plain type="danger" @click="batchDelete">
          {{ $t('admin.common.delete') }}
        </el-button>
      </template>

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
    </AdminListShell>
  </AdminPage>
</template>

<style scoped>
.mr-2 {
  margin-right: 8px;
}

.read {
  color: var(--el-text-color-secondary);
}

.unread {
  font-weight: 600;
  color: var(--el-text-color-primary);
}
</style>
