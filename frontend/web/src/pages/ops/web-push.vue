<script lang="ts" setup>
/**
 * 浏览器推送（Web Push）管理页（chat 域）
 *
 * 📍 目标位置：`src/pages/chat/web-push.vue` → 路由 `/chat/web-push`
 *   （`nuxt.config.ts` 的 `'/chat/**': {ssr: false}` 已覆盖本路径，无需改动配置）
 *
 * 覆盖后端 `chat/web_push` 模块的 8 个端点：
 *   - `GET  /vapid-public-key`  VAPID 配置状态卡（匿名可读）
 *   - `POST /subscribe`         由「浏览器订阅（本机）」卡片经 composable 触发（仅认证）
 *   - `POST /unsubscribe`       本人订阅列表「退订」/「全部退订」（仅认证）
 *   - `GET  /subscriptions`     本人订阅列表（仅认证）
 *   - `POST /send`              发送推送表单（管理端 edit）
 *   - `POST /broadcast`         广播推送表单（管理端 edit）
 *   - `GET  /stats`             订阅统计卡（管理端 view）
 *   - `POST /cleanup`           清理失效 / 过期订阅（管理端 edit）
 *
 * **无伪造**：发送 / 广播在后端未配置（缺 `pywebpush` 或 VAPID 私钥）时返回 400，
 * 拦截器弹错并 reject；本页不显示任何「已发送」的假结果。VAPID 状态卡如实展示 `reason`。
 * 「浏览器通知是否真能弹出」取决于 Service Worker 是否注册了 `push` 处理器（见页面顶部提示）。
 *
 * 权限：页面需 `module_ops:notification:view`（看统计）；发送 / 广播 / 清理按钮用
 * `module_ops:notification:edit`。
 */
import {Delete, Plus, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {onMounted, reactive, ref} from 'vue'

import {
  webPushApi,
  type WebPushBroadcastOut,
  type WebPushCleanupOut,
  type WebPushSendResponse,
  type WebPushStatsOut,
  type WebPushSubscriptionOut,
  type WebPushVapidOut,
} from '@/api'
import {useWebPushSubscription, type WebPushFailReason} from '@/composables/useWebPushSubscription'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.chat.webPush.title',
  permission: 'module_ops:notification:view',
})

const {t} = useI18n()

// ---------------------------------------------------------------- VAPID / 统计
const vapid = ref<WebPushVapidOut | null>(null)
const stats = ref<WebPushStatsOut | null>(null)
const loading = ref(false)

async function loadOverview(): Promise<void> {
  loading.value = true
  try {
    const [vapidData, statsData] = await Promise.all([
      webPushApi.vapidPublicKey(),
      webPushApi.stats(),
    ])
    vapid.value = vapidData
    stats.value = statsData
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------- 我的订阅
const subscriptions = ref<WebPushSubscriptionOut[]>([])
const subscriptionsLoading = ref(false)

async function loadSubscriptions(): Promise<void> {
  subscriptionsLoading.value = true
  try {
    subscriptions.value = await webPushApi.mySubscriptions()
  } finally {
    subscriptionsLoading.value = false
  }
}

async function unsubscribeRow(row: WebPushSubscriptionOut): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.chat.webPush.unsubscribeConfirm', {id: row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await webPushApi.unsubscribe({subscription_id: row.id})
  ElMessage.success(t('admin.chat.webPush.unsubscribed'))
  await loadSubscriptions()
}

async function unsubscribeAll(): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.chat.webPush.unsubscribeAllConfirm'),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  const result = await webPushApi.unsubscribe({})
  ElMessage.success(t('admin.chat.webPush.unsubscribedAll', {n: result.removed}))
  await loadSubscriptions()
}

// ---------------------------------------------------------------- 浏览器订阅（本机）
const {
  supported: pushSupported,
  permission: pushPermission,
  busy: pushBusy,
  hasLocalSubscription: pushHasLocal,
  enable: enableBrowserPush,
  disable: disableBrowserPush,
} = useWebPushSubscription()

function reasonText(reason: WebPushFailReason): string {
  switch (reason) {
    case 'unsupported':
      return t('admin.chat.webPush.reasonUnsupported')
    case 'permission':
      return t('admin.chat.webPush.reasonPermission')
    case 'not-configured':
      return t('admin.chat.webPush.reasonNotConfigured')
    case 'no-key':
      return t('admin.chat.webPush.reasonNoKey')
    default:
      return t('admin.chat.webPush.reasonSubscribeFailed')
  }
}

async function onEnableBrowser(): Promise<void> {
  const result = await enableBrowserPush()
  if (result.ok) {
    ElMessage.success(t('admin.chat.webPush.browserEnabled'))
    await loadSubscriptions()
  } else {
    ElMessage.warning(reasonText(result.reason))
  }
}

async function onDisableBrowser(): Promise<void> {
  const ok = await disableBrowserPush()
  if (ok) {
    ElMessage.success(t('admin.chat.webPush.browserDisabled'))
    await loadSubscriptions()
  } else {
    ElMessage.error(t('admin.chat.webPush.browserUnsupported'))
  }
}

// ---------------------------------------------------------------- 发送 / 广播
/** 解析附加数据输入：`undefined`=未填，`null`=非法，对象=合法 */
function parseExtraData(text: string): Record<string, unknown> | null | undefined {
  const trimmed = text.trim()
  if (!trimmed) return undefined
  const parsed = JSON.parse(trimmed) as unknown
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return null
  return parsed as Record<string, unknown>
}

const sendForm = reactive({
  user_id: undefined as number | undefined,
  title: '',
  body: '',
  icon: '',
  badge: '',
  dataText: '',
})
const sending = ref(false)
const sendResult = ref<WebPushSendResponse | null>(null)

async function submitSend(): Promise<void> {
  if (!sendForm.user_id || !sendForm.title.trim() || !sendForm.body.trim()) {
    ElMessage.warning(t('admin.chat.webPush.requiredFields'))
    return
  }
  let data: Record<string, unknown> | null | undefined
  try {
    data = parseExtraData(sendForm.dataText)
  } catch {
    ElMessage.warning(t('admin.chat.webPush.invalidData'))
    return
  }
  if (data === null) {
    ElMessage.warning(t('admin.chat.webPush.invalidData'))
    return
  }
  sending.value = true
  sendResult.value = null
  try {
    sendResult.value = await webPushApi.send({
      user_id: sendForm.user_id,
      title: sendForm.title.trim(),
      body: sendForm.body.trim(),
      icon: sendForm.icon.trim() || null,
      badge: sendForm.badge.trim() || null,
      data: data ?? null,
    })
    ElMessage.success(t('admin.chat.webPush.sendDone'))
  } finally {
    sending.value = false
  }
}

const broadcastForm = reactive({
  title: '',
  body: '',
  icon: '',
  badge: '',
  max_users: 500,
  dataText: '',
})
const broadcasting = ref(false)
const broadcastResult = ref<WebPushBroadcastOut | null>(null)

async function submitBroadcast(): Promise<void> {
  if (!broadcastForm.title.trim() || !broadcastForm.body.trim()) {
    ElMessage.warning(t('admin.chat.webPush.requiredFields'))
    return
  }
  let data: Record<string, unknown> | null | undefined
  try {
    data = parseExtraData(broadcastForm.dataText)
  } catch {
    ElMessage.warning(t('admin.chat.webPush.invalidData'))
    return
  }
  if (data === null) {
    ElMessage.warning(t('admin.chat.webPush.invalidData'))
    return
  }
  broadcasting.value = true
  broadcastResult.value = null
  try {
    broadcastResult.value = await webPushApi.broadcast({
      title: broadcastForm.title.trim(),
      body: broadcastForm.body.trim(),
      icon: broadcastForm.icon.trim() || null,
      badge: broadcastForm.badge.trim() || null,
      max_users: broadcastForm.max_users,
      data: data ?? null,
    })
    ElMessage.success(t('admin.chat.webPush.broadcastDone'))
  } finally {
    broadcasting.value = false
  }
}

// ---------------------------------------------------------------- 清理
const cleanupForm = reactive({max_age_days: 30, dry_run: false})
const cleaning = ref(false)
const cleanupResult = ref<WebPushCleanupOut | null>(null)

async function submitCleanup(): Promise<void> {
  cleaning.value = true
  cleanupResult.value = null
  try {
    cleanupResult.value = await webPushApi.cleanup({
      max_age_days: cleanupForm.max_age_days,
      dry_run: cleanupForm.dry_run,
    })
    ElMessage.success(t('admin.chat.webPush.cleanupDone'))
    await Promise.all([loadOverview(), loadSubscriptions()])
  } finally {
    cleaning.value = false
  }
}

async function refreshAll(): Promise<void> {
  await Promise.all([loadOverview(), loadSubscriptions()])
}

onMounted(refreshAll)
</script>

<template>
  <AdminPage :desc="$t('admin.chat.webPush.desc')" :title="$t('admin.chat.webPush.title')">
    <template #actions>
      <el-button :icon="Refresh" :loading="loading" @click="refreshAll">
        {{ $t('admin.common.refresh') }}
      </el-button>
    </template>

    <el-alert
      :closable="false"
      :title="$t('admin.chat.webPush.deliveryNote')"
      class="webpush-note"
      show-icon
      type="info"
    />

    <!-- VAPID 配置状态 -->
    <el-card class="webpush-card" shadow="never">
      <template #header>
        <span class="webpush-card__title">{{ $t('admin.chat.webPush.vapidTitle') }}</span>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item :label="$t('admin.chat.webPush.vapidConfigured')">
          <el-tag :type="vapid?.configured ? 'success' : 'danger'" size="small">
            {{ vapid?.configured ? $t('admin.common.yes') : $t('admin.common.no') }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.vapidWebpushAvailable')">
          <el-tag :type="vapid?.webpush_available ? 'success' : 'info'" size="small">
            {{ vapid?.webpush_available ? $t('admin.common.yes') : $t('admin.common.no') }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.vapidSubject')">
          {{ vapid?.subject || '-' }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.vapidPublicKey')">
          <span class="webpush-mono">{{ vapid?.public_key || '-' }}</span>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.vapidReason')" :span="2">
          {{ vapid?.reason || $t('admin.chat.webPush.vapidConfiguredOk') }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 订阅统计 -->
    <el-card class="webpush-card" shadow="never">
      <template #header>
        <span class="webpush-card__title">{{ $t('admin.chat.webPush.statsTitle') }}</span>
      </template>
      <div class="webpush-stats">
        <div class="webpush-stat">
          <p class="webpush-stat__value">{{ stats?.total_users ?? '-' }}</p>
          <p class="webpush-stat__label">{{ $t('admin.chat.webPush.statUsers') }}</p>
        </div>
        <div class="webpush-stat">
          <p class="webpush-stat__value">{{ stats?.total_subscriptions ?? '-' }}</p>
          <p class="webpush-stat__label">{{ $t('admin.chat.webPush.statSubscriptions') }}</p>
        </div>
        <div class="webpush-stat">
          <p class="webpush-stat__value">{{ stats?.average_per_user ?? '-' }}</p>
          <p class="webpush-stat__label">{{ $t('admin.chat.webPush.statAverage') }}</p>
        </div>
        <div class="webpush-stat">
          <p class="webpush-stat__value">
            {{ stats?.vapid_configured ? $t('admin.common.yes') : $t('admin.common.no') }}
          </p>
          <p class="webpush-stat__label">{{ $t('admin.chat.webPush.statVapidConfigured') }}</p>
        </div>
      </div>
    </el-card>

    <!-- 浏览器订阅（本机） -->
    <el-card class="webpush-card" shadow="never">
      <template #header>
        <span class="webpush-card__title">{{ $t('admin.chat.webPush.browserTitle') }}</span>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item :label="$t('admin.chat.webPush.browserSupported')">
          <el-tag :type="pushSupported ? 'success' : 'danger'" size="small">
            {{ pushSupported ? $t('admin.common.yes') : $t('admin.common.no') }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.browserPermission')">
          {{ pushPermission }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.browserLocal')">
          <el-tag :type="pushHasLocal ? 'success' : 'info'" size="small">
            {{ pushHasLocal ? $t('admin.chat.webPush.browserLocalOn') : $t('admin.chat.webPush.browserLocalOff') }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <div class="webpush-actions">
        <el-button
          :disabled="pushHasLocal"
          :loading="pushBusy"
          type="primary"
          @click="onEnableBrowser"
        >
          {{ $t('admin.chat.webPush.browserEnable') }}
        </el-button>
        <el-button :disabled="!pushHasLocal" :loading="pushBusy" @click="onDisableBrowser">
          {{ $t('admin.chat.webPush.browserDisable') }}
        </el-button>
      </div>
    </el-card>

    <!-- 我的订阅 -->
    <el-card class="webpush-card" shadow="never">
      <template #header>
        <span class="webpush-card__title">{{ $t('admin.chat.webPush.mySubscriptionsTitle') }}</span>
        <el-button
          :disabled="!subscriptions.length"
          class="webpush-card__action"
          link
          type="danger"
          @click="unsubscribeAll"
        >
          {{ $t('admin.chat.webPush.unsubscribeAll') }}
        </el-button>
      </template>
      <el-table v-loading="subscriptionsLoading" :data="subscriptions" border stripe>
        <el-table-column :label="$t('admin.chat.webPush.colId')" prop="id" width="150"/>
        <el-table-column
          :label="$t('admin.chat.webPush.colEndpoint')"
          min-width="220"
          prop="endpoint"
          show-overflow-tooltip
        />
        <el-table-column
          :label="$t('admin.chat.webPush.colUserAgent')"
          min-width="160"
          prop="user_agent"
          show-overflow-tooltip
        />
        <el-table-column :label="$t('admin.chat.webPush.colCreatedAt')" width="170">
          <template #default="{row}">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.chat.webPush.colLastSentAt')" width="170">
          <template #default="{row}">{{ formatDateTime(row.last_sent_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.chat.webPush.colSendCount')" prop="send_count" width="90"/>
        <el-table-column :label="$t('admin.chat.webPush.colFailCount')" prop="fail_count" width="90"/>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="90">
          <template #default="{row}">
            <el-button link type="danger" @click="unsubscribeRow(row as WebPushSubscriptionOut)">
              {{ $t('admin.chat.webPush.unsubscribe') }}
            </el-button>
          </template>
        </el-table-column>
        <template #empty>{{ $t('admin.chat.webPush.mySubscriptionsEmpty') }}</template>
      </el-table>
    </el-card>

    <!-- 发送推送 -->
    <el-card class="webpush-card" shadow="never">
      <template #header>
        <span class="webpush-card__title">{{ $t('admin.chat.webPush.sendTitle') }}</span>
      </template>
      <el-form :model="sendForm" label-width="120px">
        <el-form-item :label="$t('admin.chat.webPush.userId')" required>
          <el-input-number v-model="sendForm.user_id" :min="1" controls-position="right" style="width: 200px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.chat.webPush.messageTitle')" required>
          <el-input v-model="sendForm.title" maxlength="200"/>
        </el-form-item>
        <el-form-item :label="$t('admin.chat.webPush.messageBody')" required>
          <el-input v-model="sendForm.body" :rows="3" maxlength="2000" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.chat.webPush.iconUrl')">
          <el-input v-model="sendForm.icon" placeholder="/favicon.ico"/>
        </el-form-item>
        <el-form-item :label="$t('admin.chat.webPush.badgeUrl')">
          <el-input v-model="sendForm.badge" placeholder="/icons/badge-72x72.png"/>
        </el-form-item>
        <el-form-item :label="$t('admin.chat.webPush.extraData')">
          <el-input
            v-model="sendForm.dataText"
            :placeholder="$t('admin.chat.webPush.extraDataPlaceholder')"
            :rows="2"
            type="textarea"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            v-auth="'module_ops:notification:edit'"
            :icon="Plus"
            :loading="sending"
            type="primary"
            @click="submitSend"
          >
            {{ $t('admin.chat.webPush.sendButton') }}
          </el-button>
        </el-form-item>
      </el-form>

      <el-descriptions v-if="sendResult" :column="4" border>
        <el-descriptions-item :label="$t('admin.chat.webPush.resultTotal')">
          {{ sendResult.total }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.resultSent')">
          {{ sendResult.sent }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.resultFailed')">
          {{ sendResult.failed }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.resultPruned')">
          {{ sendResult.pruned }}
        </el-descriptions-item>
      </el-descriptions>
      <el-table v-if="sendResult && sendResult.results.length" :data="sendResult.results" border stripe>
        <el-table-column :label="$t('admin.chat.webPush.resultEndpoint')" min-width="220" prop="endpoint"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.common.status')" width="100">
          <template #default="{row}">
            <el-tag :type="row.success ? 'success' : 'danger'" size="small">
              {{ row.success ? $t('admin.common.yes') : $t('admin.common.no') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.chat.webPush.resultStatus')" prop="status" width="100"/>
        <el-table-column :label="$t('admin.chat.webPush.resultError')" min-width="200" prop="error"
                         show-overflow-tooltip/>
      </el-table>
    </el-card>

    <!-- 广播推送 -->
    <el-card class="webpush-card" shadow="never">
      <template #header>
        <span class="webpush-card__title">{{ $t('admin.chat.webPush.broadcastTitle') }}</span>
      </template>
      <el-form :model="broadcastForm" label-width="120px">
        <el-form-item :label="$t('admin.chat.webPush.messageTitle')" required>
          <el-input v-model="broadcastForm.title" maxlength="200"/>
        </el-form-item>
        <el-form-item :label="$t('admin.chat.webPush.messageBody')" required>
          <el-input v-model="broadcastForm.body" :rows="3" maxlength="2000" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.chat.webPush.iconUrl')">
          <el-input v-model="broadcastForm.icon" placeholder="/favicon.ico"/>
        </el-form-item>
        <el-form-item :label="$t('admin.chat.webPush.badgeUrl')">
          <el-input v-model="broadcastForm.badge" placeholder="/icons/badge-72x72.png"/>
        </el-form-item>
        <el-form-item :label="$t('admin.chat.webPush.maxUsers')">
          <el-input-number v-model="broadcastForm.max_users" :max="5000" :min="1" controls-position="right"
                           style="width: 200px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.chat.webPush.extraData')">
          <el-input
            v-model="broadcastForm.dataText"
            :placeholder="$t('admin.chat.webPush.extraDataPlaceholder')"
            :rows="2"
            type="textarea"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            v-auth="'module_ops:notification:edit'"
            :icon="Plus"
            :loading="broadcasting"
            type="primary"
            @click="submitBroadcast"
          >
            {{ $t('admin.chat.webPush.broadcastButton') }}
          </el-button>
        </el-form-item>
      </el-form>

      <el-descriptions v-if="broadcastResult" :column="5" border>
        <el-descriptions-item :label="$t('admin.chat.webPush.broadcastUsers')">
          {{ broadcastResult.total_users }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.resultTotal')">
          {{ broadcastResult.total }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.resultSent')">
          {{ broadcastResult.sent }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.resultFailed')">
          {{ broadcastResult.failed }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.resultPruned')">
          {{ broadcastResult.pruned }}
        </el-descriptions-item>
      </el-descriptions>
      <el-table v-if="broadcastResult && broadcastResult.details.length" :data="broadcastResult.details" border stripe>
        <el-table-column :label="$t('admin.chat.webPush.userId')" prop="user_id" width="120"/>
        <el-table-column :label="$t('admin.chat.webPush.resultTotal')" prop="total" width="100"/>
        <el-table-column :label="$t('admin.chat.webPush.resultSent')" prop="sent" width="100"/>
        <el-table-column :label="$t('admin.chat.webPush.resultPruned')" prop="pruned" width="100"/>
      </el-table>
    </el-card>

    <!-- 清理 -->
    <el-card class="webpush-card" shadow="never">
      <template #header>
        <span class="webpush-card__title">{{ $t('admin.chat.webPush.cleanupTitle') }}</span>
      </template>
      <el-form :model="cleanupForm" label-width="120px">
        <el-form-item :label="$t('admin.chat.webPush.maxAgeDays')">
          <el-input-number v-model="cleanupForm.max_age_days" :max="3650" :min="1" controls-position="right"
                           style="width: 200px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.chat.webPush.dryRun')">
          <el-switch v-model="cleanupForm.dry_run"/>
          <span class="webpush-hint">{{ $t('admin.chat.webPush.dryRunHint') }}</span>
        </el-form-item>
        <el-form-item>
          <el-button
            v-auth="'module_ops:notification:edit'"
            :icon="Delete"
            :loading="cleaning"
            type="danger"
            @click="submitCleanup"
          >
            {{ $t('admin.chat.webPush.cleanupButton') }}
          </el-button>
        </el-form-item>
      </el-form>

      <el-descriptions v-if="cleanupResult" :column="4" border>
        <el-descriptions-item :label="$t('admin.chat.webPush.cleanupScannedUsers')">
          {{ cleanupResult.scanned_users }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.cleanupScannedSubscriptions')">
          {{ cleanupResult.scanned_subscriptions }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.cleanupRemoved')">
          {{ cleanupResult.removed }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.chat.webPush.dryRun')">
          {{ cleanupResult.dry_run ? $t('admin.common.yes') : $t('admin.common.no') }}
        </el-descriptions-item>
      </el-descriptions>
      <div v-if="cleanupResult && cleanupResult.removed_ids.length" class="webpush-removed">
        <span class="webpush-hint">{{ $t('admin.chat.webPush.cleanupRemovedIds') }}:</span>
        <el-tag v-for="id in cleanupResult.removed_ids" :key="id" class="webpush-removed__tag" size="small">
          {{ id }}
        </el-tag>
      </div>
    </el-card>
  </AdminPage>
</template>

<style scoped>
.webpush-note {
  margin-bottom: var(--admin-gap-md, 16px);
}

.webpush-card {
  margin-bottom: var(--admin-gap-md, 16px);
}

.webpush-card__title {
  font-weight: 600;
}

.webpush-card__action {
  float: right;
}

.webpush-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}

.webpush-stat__value {
  font-size: 22px;
  font-weight: 700;
}

.webpush-stat__label {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.webpush-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  word-break: break-all;
}

.webpush-actions {
  margin-top: 16px;
}

.webpush-hint {
  margin-left: 12px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.webpush-removed {
  margin-top: 12px;
}

.webpush-removed__tag {
  margin: 0 6px 6px 0;
}
</style>
