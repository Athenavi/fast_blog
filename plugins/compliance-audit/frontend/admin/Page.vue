<script lang="ts" setup>
import {computed, onMounted, ref} from 'vue'

import {pluginAction} from '@/utils/pluginAction'

/**
 * 合规审计（compliance-audit 插件后台页）
 *
 * 对应 `plugins/compliance-audit/frontend/admin/Page.tsx`：
 * 默认跑一次 PCI-DSS 检查，另可按用户 ID 单独跑一遍 GDPR 检查。
 */
interface CheckItem {
  id: number
  name: string
  status: 'compliant' | 'non-compliant' | 'not_audited' | string
  detail: string
}

interface AuditReport {
  overall_status: string
  checked_at: string
  checks: CheckItem[]
}

const loading = ref(true)
const error = ref('')
const report = ref<AuditReport | null>(null)

const userId = ref('')
const auditing = ref(false)
const auditResult = ref<unknown>(null)

const isCompliant = computed(() => report.value?.overall_status === 'compliant')

async function loadReport(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const result = await pluginAction<AuditReport>('compliance-audit', 'check_pci_dss')
    report.value = result.data
    if (!result.success) error.value = result.error || '审计失败'
  } finally {
    loading.value = false
  }
}

async function auditUser(): Promise<void> {
  const id = Number.parseInt(userId.value, 10) || 0
  if (!id) return
  auditing.value = true
  try {
    const result = await pluginAction('compliance-audit', 'check_gdpr', {user_data: {user_id: id}})
    auditResult.value = result.data
    await loadReport()
  } finally {
    auditing.value = false
  }
}

function statusIcon(status: string): string {
  if (status === 'compliant') return 'circle-check'
  if (status === 'non-compliant') return 'circle-x'
  return 'shield'
}

function statusLabel(status: string): string {
  if (status === 'compliant') return '合规'
  if (status === 'non-compliant') return '不合规'
  return '未审计'
}

function statusColor(status: string): string {
  if (status === 'compliant') return 'text-success'
  if (status === 'non-compliant') return 'text-danger'
  return 'text-fg-subtle'
}

function statusBadge(status: string): string {
  if (status === 'compliant') return 'bg-success-soft text-success'
  if (status === 'non-compliant') return 'bg-danger-soft text-danger'
  return 'bg-surface-soft text-fg-muted'
}

function formatTime(value?: string): string {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

onMounted(loadReport)
</script>

<template>
  <div class="p-4">
    <div class="mb-3 flex items-center justify-end">
      <el-button :loading="loading" size="small" @click="loadReport">
        <Icon class="mr-1 h-3.5 w-3.5" name="refresh-cw"/>
        重新审计
      </el-button>
    </div>

    <p v-if="error" class="mb-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

    <!-- 总体状态 -->
    <div
      :class="isCompliant ? 'border-success bg-success-soft' : 'border-danger bg-danger-soft'"
      class="mb-6 rounded-card border p-5"
    >
      <div class="flex items-center gap-3">
        <Icon
          :class="isCompliant ? 'text-success' : 'text-danger'"
          :name="isCompliant ? 'shield-check' : 'shield-alert'"
          class="h-8 w-8"
        />
        <div>
          <p class="text-lg font-semibold text-fg">整体状态：{{ isCompliant ? '合规' : '不合规' }}</p>
          <p class="text-sm text-fg-muted">审计时间：{{ formatTime(report?.checked_at) }}</p>
        </div>
      </div>
    </div>

    <!-- 审计项 -->
    <div v-if="loading" class="space-y-3">
      <Skeleton v-for="i in 4" :key="i" class="h-16 w-full"/>
    </div>

    <EmptyState
      v-else-if="!report?.checks?.length"
      description="点击右上角「重新审计」触发一次检查"
      title="暂无审计数据"
    />

    <div v-else class="overflow-hidden rounded-card border border-line bg-surface">
      <div class="divide-y divide-line">
        <div v-for="check in report.checks" :key="check.id" class="flex items-start gap-4 px-5 py-4">
          <Icon :class="statusColor(check.status)" :name="statusIcon(check.status)" class="mt-0.5 h-5 w-5 shrink-0"/>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-fg">{{ check.name }}</p>
            <p class="mt-0.5 text-xs text-fg-subtle">{{ check.detail }}</p>
          </div>
          <span
            :class="statusBadge(check.status)"
            class="whitespace-nowrap rounded-pill px-2.5 py-0.5 text-xs font-medium"
          >{{ statusLabel(check.status) }}</span>
        </div>
      </div>
    </div>

    <!-- 按用户审计 -->
    <div class="mt-6 rounded-card border border-line bg-surface p-5">
      <h3 class="mb-3 text-sm font-semibold text-fg">审计特定用户数据</h3>
      <div class="flex gap-3">
        <el-input v-model="userId" class="max-w-xs" placeholder="输入用户 ID" @keyup.enter="auditUser"/>
        <el-button :disabled="!userId" :loading="auditing" type="primary" @click="auditUser">
          {{ auditing ? '审计中…' : '审计' }}
        </el-button>
      </div>
      <pre
        v-if="auditResult"
        class="mt-3 overflow-auto rounded-control bg-surface-soft p-3 text-xs text-fg-muted"
      >{{ JSON.stringify(auditResult, null, 2) }}</pre>
    </div>
  </div>
</template>
