<script lang="ts" setup>
import {computed, onMounted, ref, watch} from 'vue'

import {pluginAction} from '@/utils/pluginAction'

/**
 * 企业管理（enterprise 插件后台页）
 *
 * 对应 `plugins/enterprise/frontend/admin/Page.tsx`：
 * 6 个页签 —— 概览（8 个统计）+ 许可证 / 工单 / 脚本 / 日志 / 告警 五张列表（各 20 条/页）。
 * 列表用原生表格而不是 `el-table`：五个页签的列与徽标样式各不相同，
 * 配置驱动反而比模板更啰嗦（原实现也是这么写的）。
 */
interface EnterpriseItem {
  id?: number
  license_key?: string | null
  is_active?: boolean
  title?: string | null
  status?: string | null
  name?: string | null
  version?: string | null
  script_name?: string | null
  script_id?: number
  message?: string | null
  severity?: string | null
}

interface ListResult {
  items: EnterpriseItem[]
  total: number
}

interface Overview {
  total_licenses?: number
  active_licenses?: number
  open_tickets?: number
  in_progress_tickets?: number
  total_scripts?: number
  total_deployments?: number
  failed_deployments?: number
  unresolved_alerts?: number
}

type TabKey = 'overview' | 'licenses' | 'tickets' | 'scripts' | 'logs' | 'alerts'

const TABS: Array<{ key: TabKey; label: string; icon: string; action?: string }> = [
  {key: 'overview', label: '概览', icon: 'trending-up'},
  {key: 'licenses', label: '许可证', icon: 'shield', action: 'list_licenses'},
  {key: 'tickets', label: '工单', icon: 'clipboard-list', action: 'list_tickets'},
  {key: 'scripts', label: '脚本', icon: 'code-2', action: 'list_scripts'},
  {key: 'logs', label: '日志', icon: 'file-text', action: 'list_logs'},
  {key: 'alerts', label: '告警', icon: 'shield-alert', action: 'list_alerts'},
]

const PER_PAGE = 20

const tab = ref<TabKey>('overview')
const page = ref(1)
const loading = ref(false)
const error = ref('')

const overview = ref<Overview>({})
const items = ref<EnterpriseItem[]>([])
const total = ref(0)

const overviewCards = computed(() => [
  {label: '总许可证', value: overview.value.total_licenses},
  {label: '活跃许可证', value: overview.value.active_licenses},
  {label: '待处理工单', value: overview.value.open_tickets},
  {label: '进行中', value: overview.value.in_progress_tickets},
  {label: '部署脚本', value: overview.value.total_scripts},
  {label: '部署次数', value: overview.value.total_deployments},
  {label: '失败部署', value: overview.value.failed_deployments},
  {label: '未解决告警', value: overview.value.unresolved_alerts},
])

async function loadCurrent(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    if (tab.value === 'overview') {
      const result = await pluginAction<Overview>('enterprise', 'get_overview')
      overview.value = result.data ?? {}
      return
    }

    const entry = TABS.find((item) => item.key === tab.value)
    if (!entry?.action) return

    const result = await pluginAction<ListResult>('enterprise', entry.action, {
      page: page.value,
      per_page: PER_PAGE,
    })
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

function tagClass(kind: 'success' | 'warning' | 'danger' | 'muted'): string {
  if (kind === 'success') return 'bg-success-soft text-success'
  if (kind === 'warning') return 'bg-warning-soft text-warning'
  if (kind === 'danger') return 'bg-danger-soft text-danger'
  return 'bg-surface-soft text-fg-muted'
}

watch(page, loadCurrent)
onMounted(loadCurrent)
</script>

<template>
  <div class="p-4">
    <!-- 页签 -->
    <div class="mb-6 flex flex-wrap gap-2">
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

    <!-- 概览 -->
    <div v-if="tab === 'overview'" class="grid grid-cols-2 gap-4 md:grid-cols-4">
      <div v-for="card in overviewCards" :key="card.label" class="rounded-card border border-line bg-surface p-4">
        <p class="mb-1 text-xs text-fg-muted">{{ card.label }}</p>
        <p class="text-2xl font-bold text-fg">{{ card.value ?? '—' }}</p>
      </div>
    </div>

    <!-- 列表 -->
    <template v-else>
      <div v-if="loading" class="space-y-3">
        <Skeleton v-for="i in 5" :key="i" class="h-14 w-full"/>
      </div>

      <EmptyState v-else-if="!items.length" title="暂无数据"/>

      <div v-else class="overflow-hidden rounded-card border border-line bg-surface">
        <table class="w-full text-sm">
          <thead class="bg-surface-soft text-xs uppercase text-fg-muted">
          <tr>
            <template v-if="tab === 'licenses'">
              <th class="px-5 py-3 text-left font-semibold">Key</th>
              <th class="px-5 py-3 text-right font-semibold">状态</th>
            </template>
            <template v-else-if="tab === 'tickets'">
              <th class="px-5 py-3 text-left font-semibold">标题</th>
              <th class="px-5 py-3 text-left font-semibold">状态</th>
            </template>
            <template v-else-if="tab === 'scripts'">
              <th class="px-5 py-3 text-left font-semibold">名称</th>
              <th class="px-5 py-3 text-right font-semibold">版本</th>
            </template>
            <template v-else-if="tab === 'logs'">
              <th class="px-5 py-3 text-left font-semibold">脚本</th>
              <th class="px-5 py-3 text-left font-semibold">状态</th>
            </template>
            <template v-else>
              <th class="px-5 py-3 text-left font-semibold">消息</th>
              <th class="px-5 py-3 text-left font-semibold">级别</th>
            </template>
          </tr>
          </thead>
          <tbody class="divide-y divide-line">
          <tr v-for="(item, index) in items" :key="item.id ?? index" class="hover:bg-surface-soft">
            <template v-if="tab === 'licenses'">
              <td class="max-w-[320px] truncate px-5 py-4 font-mono text-fg">{{
                  item.license_key || `#${item.id}`
                }}
              </td>
              <td class="px-5 py-4 text-right">
                  <span :class="tagClass(item.is_active ? 'success' : 'muted')"
                        class="rounded-pill px-2 py-0.5 text-xs">
                    {{ item.is_active ? '活跃' : '停用' }}
                  </span>
              </td>
            </template>

            <template v-else-if="tab === 'tickets'">
              <td class="px-5 py-4 font-medium text-fg">{{ item.title || `#${item.id}` }}</td>
              <td class="px-5 py-4">
                  <span
                    :class="tagClass(item.status === 'open' ? 'warning' : item.status === 'resolved' ? 'success' : 'muted')"
                    class="rounded-pill px-2 py-0.5 text-xs"
                  >{{ item.status || '—' }}</span>
              </td>
            </template>

            <template v-else-if="tab === 'scripts'">
              <td class="px-5 py-4 font-medium text-fg">{{ item.name || `#${item.id}` }}</td>
              <td class="px-5 py-4 text-right text-fg-muted">{{ item.version || '1.0' }}</td>
            </template>

            <template v-else-if="tab === 'logs'">
              <td class="px-5 py-4 text-fg">{{ item.script_name || `#${item.script_id}` }}</td>
              <td class="px-5 py-4">
                  <span
                    :class="tagClass(item.status === 'success' ? 'success' : 'danger')"
                    class="rounded-pill px-2 py-0.5 text-xs"
                  >{{ item.status || '—' }}</span>
              </td>
            </template>

            <template v-else>
              <td class="max-w-xs truncate px-5 py-4 text-fg">{{ item.message || `#${item.id}` }}</td>
              <td class="px-5 py-4">
                  <span
                    :class="tagClass(item.severity === 'critical' ? 'danger' : 'warning')"
                    class="rounded-pill px-2 py-0.5 text-xs"
                  >{{ item.severity || 'info' }}</span>
              </td>
            </template>
          </tr>
          </tbody>
        </table>
      </div>

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
