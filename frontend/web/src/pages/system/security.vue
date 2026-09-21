<script lang="ts" setup>
/**
 * 安全中心（T5-11 批次 3）
 *
 * 对齐 v3 `/system/security`：总览聚合（24h）+ 登录尝试列表 + 令牌黑名单。
 * 锁定账户管理由 `/system/log` 覆盖，本页不重复。
 */
import {Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, ref} from 'vue'

import {type BlacklistItem, type LoginAttemptItem, securityApi, type SecurityOverview,} from '@/api'
import type {PageQuery} from '@/api/types'
import {useTable} from '@/hooks/useTable'

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

// ---- 登录尝试 ----
interface AttemptQueryForm extends PageQuery {
  username?: string
  is_success?: boolean
}

const {
  list: attemptList,
  loading: attemptLoading,
  total: attemptTotal,
  page: attemptPage,
  pageSize: attemptPageSize,
  query: attemptQuery,
  search: attemptSearch,
  reset: attemptReset,
  load: attemptLoad,
  onPageChange: onAttemptPageChange,
  onSizeChange: onAttemptSizeChange,
} = useTable<LoginAttemptItem, AttemptQueryForm>({
  fetcher: (params) => securityApi.attempts(params),
  defaultQuery: {username: '', is_success: undefined},
  syncUrl: true,
})

// ---- 黑名单 ----
const {
  list: blacklist,
  loading: blacklistLoading,
  total: blacklistTotal,
  page: blacklistPage,
  pageSize: blacklistPageSize,
  load: blacklistLoad,
  onPageChange: onBlacklistPageChange,
  onSizeChange: onBlacklistSizeChange,
} = useTable<BlacklistItem, PageQuery>({
  fetcher: (params) => securityApi.blacklist(params),
})

async function onDeleteBlacklist(row: BlacklistItem) {
  await ElMessageBox.confirm(t('admin.system.security.deleteBlacklistConfirm'), t('admin.common.notice'), {
    type: 'warning',
  })
  await securityApi.removeBlacklist(row.id)
  ElMessage.success(t('admin.common.delete'))
  await Promise.all([loadOverview(), blacklistLoad()])
}
</script>

<template>
  <div class="page-container">
    <!-- 统计卡 -->
    <div v-if="stats.length" class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-5">
      <el-card v-for="item in stats" :key="item.label" shadow="never">
        <div class="text-xs text-fg-subtle">{{ item.label }}</div>
        <div class="mt-1 text-xl font-semibold text-fg">{{ item.value }}</div>
      </el-card>
    </div>

    <el-card shadow="never">
      <el-tabs v-model="activeTab">
        <!-- 登录尝试 -->
        <el-tab-pane :label="$t('admin.system.security.tabAttempts')" name="attempts">
          <el-form :inline="true" :model="attemptQuery" @submit.prevent="attemptSearch()">
            <el-form-item :label="$t('admin.system.security.username')">
              <el-input
                v-model="attemptQuery.username"
                :placeholder="$t('admin.system.security.usernamePlaceholder')"
                clearable
                style="width: 180px"
                @keyup.enter="attemptSearch()"
              />
            </el-form-item>
            <el-form-item :label="$t('admin.system.security.result')">
              <el-select
                v-model="attemptQuery.is_success"
                :placeholder="$t('admin.common.all')"
                clearable
                style="width: 110px"
              >
                <el-option :label="$t('admin.system.security.resultSuccess')" :value="true"/>
                <el-option :label="$t('admin.system.security.resultFailure')" :value="false"/>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="attemptSearch()">
                {{ $t('admin.common.search') }}
              </el-button>
              <el-button :icon="Refresh" @click="attemptReset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>

          <AdminTableSkeleton v-if="attemptLoading && !attemptList.length" :rows="5"/>

          <AdminEmpty v-else-if="!attemptLoading && !attemptList.length" :title="$t('admin.common.empty')"/>
          <el-table v-else v-loading="attemptLoading" :data="attemptList" border stripe>
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
          </el-table>

          <el-pagination
            :current-page="attemptPage"
            :page-size="attemptPageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="attemptTotal"
            background
            class="table-pagination"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="onAttemptPageChange"
            @size-change="onAttemptSizeChange"
          />
        </el-tab-pane>

        <!-- 令牌黑名单 -->
        <el-tab-pane :label="$t('admin.system.security.tabBlacklist')" name="blacklist">
          <el-table v-loading="blacklistLoading" :data="blacklist" border stripe>
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
          </el-table>

          <el-pagination
            :current-page="blacklistPage"
            :page-size="blacklistPageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="blacklistTotal"
            background
            class="table-pagination"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="onBlacklistPageChange"
            @size-change="onBlacklistSizeChange"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>
