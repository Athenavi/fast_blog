<script lang="ts" setup>
import {computed, onMounted, ref} from 'vue'

import {cacheApi, type CacheStats, monitorApi, type OnlineSession, type OnlineStats, type ServerInfo} from '@/api'
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
  title: '系统总览',
  permission: 'module_system:monitor:view',
})

const PAGE_SIZE = 10

const loading = ref(false)
const server = ref<ServerInfo | null>(null)
const online = ref<OnlineStats | null>(null)
const cache = ref<CacheStats | null>(null)

const sessions = ref<OnlineSession[]>([])
const sessionsTotal = ref(0)
const page = ref(1)
const kicking = ref<number | null>(null)

const multiLevel = computed(() => cache.value?.multi_level ?? {})

async function load(): Promise<void> {
  loading.value = true
  try {
    const [overview, cacheStats, sessionPage] = await Promise.all([
      monitorApi.overview(),
      cacheApi.stats().catch(() => null),
      monitorApi.onlineList({page: page.value, page_size: PAGE_SIZE}).catch(() => null),
    ])
    server.value = overview?.server ?? null
    online.value = overview?.online ?? null
    cache.value = cacheStats
    sessions.value = sessionPage?.items ?? []
    sessionsTotal.value = sessionPage?.total ?? 0
  } finally {
    loading.value = false
  }
}

async function kick(row: OnlineSession): Promise<void> {
  await ElMessageBox.confirm(
    `确定把会话 #${row.id}（用户 ${row.user_id}）强制下线吗？`,
    '提示',
    {type: 'warning'},
  )
  kicking.value = row.id
  try {
    await monitorApi.kick(row.id)
    ElMessage.success('已强制下线')
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

/** 进度条颜色随占用率变化 */
function barColor(percent: number): string {
  if (percent >= 90) return '#ef4444'
  if (percent >= 75) return '#f59e0b'
  return '#10b981'
}

onMounted(load)
</script>

<template>
  <div class="hub">
    <div class="mb-3 flex flex-wrap items-center gap-3">
      <el-button :loading="loading" @click="load">
        <Icon class="mr-1 h-3.5 w-3.5" name="refresh-cw"/>
        刷新
      </el-button>
      <span class="text-xs text-fg-subtle">在线判定窗口：{{ online?.window_seconds ?? 1800 }} 秒</span>
    </div>

    <!-- 服务器信息 -->
    <el-card class="mb-4" shadow="never">
      <template #header><span class="font-medium">服务器</span></template>

      <div v-if="loading && !server" class="space-y-3">
        <Skeleton class="h-5 w-64"/>
        <Skeleton class="h-5 w-48"/>
      </div>

      <template v-else-if="server">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="操作系统">{{ server.platform }}</el-descriptions-item>
          <el-descriptions-item label="主机名">{{ server.hostname }}</el-descriptions-item>
          <el-descriptions-item label="Python">{{ server.python_version }}</el-descriptions-item>
          <el-descriptions-item label="启动时间">{{ formatDateTime(server.boot_time) }}</el-descriptions-item>
          <el-descriptions-item label="已运行">{{ formatUptime(server.uptime_seconds) }}</el-descriptions-item>
          <el-descriptions-item label="进程">
            PID {{ server.process.pid }} · 内存 {{ formatFileSize(server.process.rss) }} · 线程
            {{ server.process.threads }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div class="gauge">
            <div class="gauge__head">
              <span>CPU（{{ server.cpu.count }} 核）</span>
              <span class="gauge__value">{{ server.cpu.percent.toFixed(1) }}%</span>
            </div>
            <div class="gauge__track">
              <div :style="{width: `${server.cpu.percent}%`, backgroundColor: barColor(server.cpu.percent)}"
                   class="gauge__fill"/>
            </div>
            <p v-if="server.cpu.load_avg.length" class="gauge__foot">
              负载：{{ server.cpu.load_avg.join(' / ') }}
            </p>
          </div>

          <div class="gauge">
            <div class="gauge__head">
              <span>内存</span>
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
          <el-table-column label="挂载点" min-width="160">
            <template #default="{row}">
              <span class="font-mono text-xs">{{ row.mountpoint }}</span>
              <span class="ml-2 text-xs text-fg-subtle">{{ row.fstype }}</span>
            </template>
          </el-table-column>
          <el-table-column label="容量" width="200">
            <template #default="{row}">{{ formatFileSize(row.used) }} / {{ formatFileSize(row.total) }}</template>
          </el-table-column>
          <el-table-column label="使用率" width="160">
            <template #default="{row}">
              <div class="gauge__track">
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
        <span class="font-medium">在线用户</span>
        <span class="ml-3 text-xs text-fg-subtle">
          活跃 {{ online?.active_sessions ?? '—' }} · 窗口内活跃 {{ online?.recent_sessions ?? '—' }} ·
          去重用户 {{ online?.unique_users ?? '—' }}
        </span>
      </template>

      <EmptyState v-if="!sessions.length && !loading" description="当前没有活跃会话" title="暂无在线用户"/>

      <el-table v-else v-loading="loading" :data="sessions" border size="small">
        <el-table-column label="用户" width="90">
          <template #default="{row}">#{{ row.user_id }}</template>
        </el-table-column>
        <el-table-column label="设备" min-width="220">
          <template #default="{row}">
            <span class="block truncate text-xs">{{ row.device_info || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="IP" width="140">
          <template #default="{row}">{{ row.ip_address || '—' }}</template>
        </el-table-column>
        <el-table-column label="位置" width="120">
          <template #default="{row}">{{ row.location || '—' }}</template>
        </el-table-column>
        <el-table-column label="最后活动" width="170">
          <template #default="{row}">{{ formatDateTime(row.last_activity) }}</template>
        </el-table-column>
        <el-table-column align="right" label="操作" width="110">
          <template #default="{row}">
            <el-button :loading="kicking === row.id" link type="danger" @click="kick(row)">强制下线</el-button>
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
        <span class="font-medium">缓存</span>
        <NuxtLink class="ml-3 text-xs text-primary hover:underline" to="/system/cache">前往缓存管理 →</NuxtLink>
      </template>

      <p v-if="multiLevel.error" class="text-sm text-danger">统计失败：{{ multiLevel.error }}</p>

      <div v-else class="grid grid-cols-3 gap-4">
        <div class="gauge">
          <p class="gauge__label">总请求</p>
          <p class="gauge__big">{{ multiLevel.total_requests ?? '—' }}</p>
        </div>
        <div class="gauge">
          <p class="gauge__label">总命中</p>
          <p class="gauge__big">{{ multiLevel.total_hits ?? '—' }}</p>
        </div>
        <div class="gauge">
          <p class="gauge__label">命中率</p>
          <p class="gauge__big">{{ multiLevel.hit_rate ?? '—' }}</p>
        </div>
      </div>
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
