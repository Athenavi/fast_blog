<script lang="ts" setup>
/**
 * 安全中心（T5-11 批次 3）
 *
 * 对齐 v3 `/system/security`：总览聚合（24h）+ 登录尝试列表 + 令牌黑名单。
 * 锁定账户管理由 `/system/log` 覆盖，本页不重复。
 */
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, ref} from 'vue'

import {type BlacklistItem, type LoginAttemptItem, securityApi, type SecurityOverview,} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.security.title',
  permission: 'module_system:security:view',
})

const {t} = useI18n()

const activeTab = ref<'attempts' | 'blacklist'>('attempts')
const overview = ref<SecurityOverview | null>(null)

async function loadOverview(): Promise<void> {
  try {
    overview.value = await securityApi.overview()
  } catch {
    overview.value = null
  }
}

onMounted(loadOverview)

/** 统计卡：依赖 overview 响应式重建 */
const stats = computed<Array<{ label: string; value: number | string }>>(() => {
  const o = overview.value
  if (!o) return []
  return [
    {label: t('admin.system.security.statAttempts'), value: o.attempts_24h},
    {label: t('admin.system.security.statFailures'), value: o.failures_24h},
    {label: t('admin.system.security.statSuccessRate'), value: `${(o.success_rate * 100).toFixed(1)}%`},
    {label: t('admin.system.security.statLocked'), value: o.locked_users},
    {label: t('admin.system.security.statBlacklist'), value: o.blacklist_count},
  ]
})

// ---- 登录尝试（筛选条件写入 URL）----
interface AttemptQueryForm extends PageQuery {
  username?: string
  is_success?: boolean
}

const attempts = useAdminList<LoginAttemptItem, AttemptQueryForm>({
  fetcher: (params) => securityApi.attempts(params),
  defaultQuery: {username: '', is_success: undefined},
  syncUrl: true,
})

// ---- 令牌黑名单（无筛选条件，因此不写 URL，避免与上一个列表争用 query）----
const blacklist = useAdminList<BlacklistItem, PageQuery>({
  fetcher: (params) => securityApi.blacklist(params),
})

async function onDeleteBlacklist(row: BlacklistItem) {
  await ElMessageBox.confirm(t('admin.system.security.deleteBlacklistConfirm'), t('admin.common.notice'), {
    type: 'warning',
  })
  await securityApi.removeBlacklist(row.id)
  ElMessage.success(t('admin.common.delete'))
  await Promise.all([loadOverview(), blacklist.reload()])
}
</script>

<template>
  <AdminPage :desc="$t('admin.system.security.desc')" :title="$t('admin.system.security.title')">
    <!-- 统计卡：页面级信息，放在列表壳之外 -->
    <div v-if="stats.length" class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-5">
      <el-card v-for="item in stats" :key="item.label" shadow="never">
        <div class="text-xs text-fg-subtle">{{ item.label }}</div>
        <div class="mt-1 text-xl font-semibold text-fg">{{ item.value }}</div>
      </el-card>
    </div>

    <el-tabs v-model="activeTab">
      <!-- 登录尝试 -->
      <el-tab-pane :label="$t('admin.system.security.tabAttempts')" name="attempts">
        <AdminListShell
          :empty-desc="attempts.hasFilters.value
            ? $t('admin.system.security.emptyFiltered')
            : $t('admin.system.security.emptyDesc')"
          :empty-title="$t('admin.system.security.emptyTitle')"
          :failed="attempts.failed.value"
          :loading="attempts.loading.value"
          :page="attempts.page.value"
          :page-size="attempts.pageSize.value"
          :rows="attempts.rows.value"
          :selectable="false"
          :total="attempts.total.value"
          @refresh="attempts.reload"
          @reset="attempts.reset"
          @search="attempts.search"
          @page-change="attempts.onPageChange"
          @size-change="attempts.onSizeChange"
        >
          <template #filters>
            <el-form-item :label="$t('admin.system.security.username')">
              <el-input
                v-model="attempts.query.username"
                clearable
                :placeholder="$t('admin.system.security.usernamePlaceholder')"
                style="width: 180px"
                @keyup.enter="attempts.search()"
              />
            </el-form-item>
            <el-form-item :label="$t('admin.system.security.result')">
              <el-select
                v-model="attempts.query.is_success"
                clearable
                :placeholder="$t('admin.common.all')"
                style="width: 110px"
              >
                <el-option :label="$t('admin.system.security.resultSuccess')" :value="true"/>
                <el-option :label="$t('admin.system.security.resultFailure')" :value="false"/>
              </el-select>
            </el-form-item>
          </template>

          <el-table-column label="ID" prop="id" width="80"/>
          <el-table-column :label="$t('admin.system.security.username')" min-width="130" prop="username"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.ipAddress')" min-width="130" prop="ip_address"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.result')" width="90">
            <template #default="{ row }">
              <el-tag :type="(row as LoginAttemptItem).is_success ? 'success' : 'danger'" size="small">
                {{
                  (row as LoginAttemptItem).is_success
                    ? $t('admin.system.security.resultSuccess')
                    : $t('admin.system.security.resultFailure')
                }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.system.security.failureReason')" min-width="150" prop="failure_reason"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.userAgent')" min-width="200" prop="user_agent"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.common.createdAt')" min-width="170" prop="created_at"
                           show-overflow-tooltip/>
        </AdminListShell>
      </el-tab-pane>

      <!-- 令牌黑名单 -->
      <el-tab-pane :label="$t('admin.system.security.tabBlacklist')" name="blacklist">
        <AdminListShell
          :empty-desc="$t('admin.system.security.blacklistEmptyDesc')"
          :empty-title="$t('admin.system.security.blacklistEmptyTitle')"
          :failed="blacklist.failed.value"
          :loading="blacklist.loading.value"
          :page="blacklist.page.value"
          :page-size="blacklist.pageSize.value"
          :rows="blacklist.rows.value"
          :selectable="false"
          :total="blacklist.total.value"
          @refresh="blacklist.reload"
          @page-change="blacklist.onPageChange"
          @size-change="blacklist.onSizeChange"
        >
          <el-table-column label="ID" prop="id" width="80"/>
          <el-table-column :label="$t('admin.system.security.tokenIdentifier')" min-width="220"
                           prop="token_identifier" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.reason')" min-width="150" prop="reason"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.expiresAt')" min-width="170" prop="expires_at"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.common.createdAt')" min-width="170" prop="created_at"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.common.actions')" fixed="right" width="100">
            <template #default="{ row }">
              <el-button
                v-auth="'module_system:security:delete'"
                link
                type="danger"
                @click="onDeleteBlacklist(row as BlacklistItem)"
              >
                {{ $t('admin.common.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </AdminListShell>
      </el-tab-pane>
    </el-tabs>
  </AdminPage>
</template>
