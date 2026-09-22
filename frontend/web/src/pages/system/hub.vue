<script lang="ts" setup>
const {t} = useI18n()
import {computed, onMounted, ref} from 'vue'

import {
  cacheApi,
  type CacheStats,
  installApi,
  type InstallStatus,
  monitorApi,
  type OnlineSession,
  type OnlineStats,
  type ServerInfo,
} from '@/api'
import {Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {formatDateTime, formatFileSize} from '@/utils/format'

/**
 * 系统总览（v3 `system/monitor` + `system/cache`）
 *
 * 对应原 astro 后台的 `admin/system-hub` / `admin/system` 聚合页 —— 同属「无接口页面」清单，
 * React 原实现已随 `archive/` 删除。功能设计参考官方 FastApiAdmin 的
 * `modules/monitor/*`（server + online）与它的 system-hub 页，实现按 fast_blog v3 的端点重写。
 *
 * 页面构成：服务器信息（CPU/内存/磁盘/进程）+ 在线会话（含强制下线）+ 缓存概览。
 */
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.hub.systemOverview',
  permission: 'module_system:monitor:view',
})

const PAGE_SIZE = 10

const loading = ref(false)
/** 加载失败（用于错误态与重试） */
const loadFailed = ref(false)
const server = ref<ServerInfo | null>(null)
const online = ref<OnlineStats | null>(null)
const cache = ref<CacheStats | null>(null)
const install = ref<InstallStatus | null>(null)

const sessions = ref<OnlineSession[]>([])
const sessionsTotal = ref(0)
const page = ref(1)
const kicking = ref<number | null>(null)

const multiLevel = computed(() => cache.value?.multi_level ?? {})

async function load(): Promise<void> {
  loading.value = true
  try {
    const [overview, cacheStats, sessionPage, installStatus] = await Promise.all([
      monitorApi.overview(),
      cacheApi.stats().catch(() => null),
      monitorApi.onlineList({page: page.value, page_size: PAGE_SIZE}).catch(() => null),
      installApi.status().catch(() => null),
    ])
    server.value = overview?.server ?? null
    online.value = overview?.online ?? null
    cache.value = cacheStats
    install.value = installStatus
    sessions.value = sessionPage?.items ?? []
    sessionsTotal.value = sessionPage?.total ?? 0
  } catch {
    // 失败时置错误态，避免把「请求失败」显示成「暂无数据」
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

async function kick(row: OnlineSession): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.system.hub.kickConfirm', {id: row.id, user: row.user_id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  kicking.value = row.id
  try {
    await monitorApi.kick(row.id)
    ElMessage.success(t('admin.system.hub.sessionTerminated'))
    await load()
  } finally {
    kicking.value = null
  }
}

/** 秒 → `3d 4h 12m` */
function formatUptime(seconds?: number): string {
  if (!seconds || seconds < 0) return '—'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return [days ? `${days}d` : '', hours ? `${hours}h` : '', `${minutes}m`].filter(Boolean).join(' ')
}

/** 进度条颜色随占用率变化（引用语义令牌，深浅色与自选配色自动跟随） */
function barColor(percent: number): string {
  if (percent >= 90) return 'var(--admin-danger)'
  if (percent >= 75) return 'var(--admin-warning)'
  return 'var(--admin-success)'
}

onMounted(load)
</script>

<template>
  <div class="hub">
    <div class="mb-3 flex flex-wrap items-center gap-3">
      <el-button :loading="loading" @click="load">
        <Icon class="mr-1 h-3.5 w-3.5" name="refresh-cw"/>
        {{ $t('common.refresh') }}
      </el-button>
      <span class="text-xs text-fg-subtle">{{
          $t('admin.system.hub.onlineWindow', {seconds: online?.window_seconds ?? 1800})
        }}</span>
    </div>

    <!-- 服务器信息 -->
    <el-card class="mb-4" shadow="never">
      <template #header><span class="font-medium">{{ $t('admin.system.hub.server') }}</span></template>

      <div v-if="loading && !server" class="space-y-3">
        <Skeleton class="h-5 w-64"/>
        <Skeleton class="h-5 w-48"/>
      </div>

      <template v-else-if="server">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item :label="$t('admin.system.hub.operatingSystem')">{{
              server.platform
            }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.system.hub.hostname')">{{ server.hostname }}</el-descriptions-item>
          <el-descriptions-item label="Python">{{ server.python_version }}</el-descriptions-item>
          <el-descriptions-item :label="$t('admin.system.hub.bootTime')">{{
              formatDateTime(server.boot_time)
            }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.system.hub.uptime')">{{
              formatUptime(server.uptime_seconds)
            }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.system.hub.process')">
            {{
              $t('admin.system.hub.processInfo', {
                pid: server.process.pid,
                mem: formatFileSize(server.process.rss),
                threads: server.process.threads
              })
            }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div class="gauge">
            <div class="gauge__head">
              <span>{{ $t('admin.system.hub.cpuCores', {count: server.cpu.count}) }}</span>
              <span class="gauge__value">{{ server.cpu.percent.toFixed(1) }}%</span>
            </div>
            <div class="gauge__track">
              <div :style="{width: `${server.cpu.percent}%`, backgroundColor: barColor(server.cpu.percent)}"
                   class="gauge__fill"/>
            </div>
            <p v-if="server.cpu.load_avg.length" class="gauge__foot">
              {{ $t('admin.system.hub.load', {load: server.cpu.load_avg.join(' / ')}) }}
            </p>
          </div>

          <div class="gauge">
            <div class="gauge__head">
              <span>{{ $t('admin.system.hub.memory') }}</span>
              <span class="gauge__value">{{ server.memory.percent.toFixed(1) }}%</span>
            </div>
            <div class="gauge__track">
              <div :style="{width: `${server.memory.percent}%`, backgroundColor: barColor(server.memory.percent)}"
                   class="gauge__fill"/>
            </div>
            <p class="gauge__foot">
              {{ formatFileSize(server.memory.used) }} / {{ formatFileSize(server.memory.total) }}
            </p>
          </div>
        </div>

        <el-table v-if="server.disks.length" :data="server.disks" border class="mt-4" size="small">
          <el-table-column :label="$t('admin.system.hub.mountPoint')" min-width="160">
            <template #default="{row}">
              <span class="font-mono text-xs">{{ row.mountpoint }}</span>
              <span class="ml-2 text-xs text-fg-subtle">{{ row.fstype }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.system.hub.capacity')" width="200">
            <template #default="{row}">{{ formatFileSize(row.used) }} / {{ formatFileSize(row.total) }}</template>
          </el-table-column>
          <el-table-column :label="$t('admin.system.hub.usage')" width="160">
            <template #default="{row}">
              <div
                :aria-valuenow="Math.round(row.percent)"
                aria-valuemax="100"
                aria-valuemin="0"
                class="gauge__track"
                role="progressbar"
              >
                <div :style="{width: `${row.percent}%`, backgroundColor: barColor(row.percent)}" class="gauge__fill"/>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="%" width="70">
            <template #default="{row}">{{ row.percent.toFixed(1) }}</template>
          </el-table-column>
        </el-table>
      </template>
    </el-card>

    <!-- 在线会话 -->
    <el-card class="mb-4" shadow="never">
      <template #header>
        <span class="font-medium">{{ $t('admin.system.hub.onlineUsers') }}</span>
        <span class="ml-3 text-xs text-fg-subtle">
          {{
            $t('admin.system.hub.onlineSummary', {
              active: online?.active_sessions ?? '—',
              recent: online?.recent_sessions ?? '—',
              unique: online?.unique_users ?? '—'
            })
          }}
        </span>
      </template>

      <EmptyState v-if="!sessions.length && !loading" :description="$t('admin.system.hub.noActiveSessions')"
                  :title="$t('admin.system.hub.noOnlineUsers')"/>

      <AdminTableSkeleton v-if="loading && !sessions.length" :rows="5"/>

      <AdminEmpty
        v-else-if="!loading && !sessions.length"
        :title="loadFailed ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
        :variant="loadFailed ? 'error' : 'default'"
      >
        <el-button v-if="loadFailed" :icon="Refresh" @click="load()">
          {{ $t('admin.common.retry') }}
        </el-button>
      </AdminEmpty>

      <el-table v-else v-loading="loading" :data="sessions" border size="small">
        <el-table-column :label="$t('user.title')" width="90">
          <template #default="{row}">#{{ row.user_id }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.hub.device')" min-width="220">
          <template #default="{row}">
            <span class="block truncate text-xs">{{ row.device_info || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="IP" width="140">
          <template #default="{row}">{{ row.ip_address || '—' }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.hub.location')" width="120">
          <template #default="{row}">{{ row.location || '—' }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.hub.lastActivity')" width="170">
          <template #default="{row}">{{ formatDateTime(row.last_activity) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" align="right" width="110">
          <template #default="{row}">
            <el-button :loading="kicking === row.id" link type="danger" @click="kick(row)">
              {{ $t('admin.system.hub.terminateSession') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="sessionsTotal > PAGE_SIZE"
        v-model:current-page="page"
        :page-size="PAGE_SIZE"
        :total="sessionsTotal"
        class="mt-3 justify-end"
        layout="total, prev, pager, next"
        @current-change="load"
      />
    </el-card>

    <!-- 缓存概览 -->
    <el-card shadow="never">
      <template #header>
        <span class="font-medium">{{ $t('admin.system.hub.cache') }}</span>
        <NuxtLink class="ml-3 text-xs text-primary hover:underline" to="/system/cache">
          {{ $t('admin.system.hub.openCacheManagement') }}
        </NuxtLink>
      </template>

      <p v-if="multiLevel.error" class="text-sm text-danger">
        {{ $t('admin.common.statsFailed', {error: multiLevel.error}) }}</p>

      <div v-else class="grid grid-cols-3 gap-4">
        <div class="gauge">
          <p class="gauge__label">{{ $t('admin.system.hub.requests') }}</p>
          <p class="gauge__big">{{ multiLevel.total_requests ?? '—' }}</p>
        </div>
        <div class="gauge">
          <p class="gauge__label">{{ $t('admin.system.hub.hits') }}</p>
          <p class="gauge__big">{{ multiLevel.total_hits ?? '—' }}</p>
        </div>
        <div class="gauge">
          <p class="gauge__label">{{ $t('admin.system.hub.hitRate') }}</p>
          <p class="gauge__big">{{ multiLevel.hit_rate ?? '—' }}</p>
        </div>
      </div>
    </el-card>

    <!-- 环境自检（批次 11：`GET /system/install/status`，公开只读） -->
    <el-card class="mt-4" shadow="never">
      <template #header>
        <span class="font-medium">{{ $t('admin.system.hub.install') }}</span>
      </template>
      <el-descriptions v-if="install" :column="2" border size="small">
        <el-descriptions-item :label="$t('admin.system.hub.installDatabase')">
          <el-tag :type="install.database.ok ? 'success' : 'danger'" size="small">
            {{
              install.database.ok ? $t('admin.system.hub.installOk') : (install.database.error || $t('admin.system.hub.installFail'))
            }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.system.hub.installInstalled')">
          <el-tag :type="install.installed ? 'success' : 'warning'" size="small">
            {{ install.installed ? $t('admin.common.yes') : $t('admin.common.no') }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.system.hub.installMigration')">
          <el-tag :type="install.migration.up_to_date ? 'success' : 'warning'" size="small">
            {{ install.migration.current || '—' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.system.hub.installRealtime')">
          <el-tag :type="install.realtime_available ? 'success' : 'info'" size="small">
            {{ install.realtime_available ? $t('admin.common.enabled') : $t('admin.common.disabled') }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <p v-else class="text-sm text-fg-muted">{{ $t('admin.system.hub.installUnavailable') }}</p>
    </el-card>
  </div>
</template>

<style scoped>
.hub {
  padding: 16px;
}

.gauge {
  padding: 10px 12px;
  background-color: var(--color-surface-soft);
  border-radius: var(--radius-control);
}

.gauge__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 13px;
  color: var(--color-fg);
}

.gauge__value {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.gauge__label {
  margin: 0 0 4px;
  font-size: 12px;
  color: var(--color-fg-muted);
}

.gauge__big {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg);
}

.gauge__foot {
  margin: 6px 0 0;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg-muted);
}

.gauge__track {
  height: 8px;
  overflow: hidden;
  background-color: var(--color-line);
  border-radius: 9999px;
}

.gauge__fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease;
}
</style>
