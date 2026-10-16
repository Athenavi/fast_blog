<script lang="ts" setup>
/**
 * 维护模式控制台（/system/maintenance，任务 14c）
 *
 * 对齐后端 9 个端点：当前状态（公开 `status`）、人工开关、提示语、定时窗口、IP 白名单。
 *
 * 「以匿名访客视角预览」不额外开接口 —— 复用公开的 `status`：它按**请求方 IP** 计算
 * `active`，恰好等于普通访客会看到的判定（若管理员自己的 IP 在白名单中，预览会显示
 * 「正常运行」，提示文案里已说明这一点）。
 */
import {Delete, Plus, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {maintenanceApi, type MaintenanceConfig, type MaintenanceStatus} from '@/api'
import {formatDateTime, localTimeZone} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.maintenance.title',
  permission: 'module_system:setting:view',
})

const {t} = useI18n()

const loading = ref(false)
const failed = ref(false)
const config = ref<MaintenanceConfig | null>(null)
const status = ref<MaintenanceStatus | null>(null)

const messageDraft = ref('')
const scheduleForm = reactive<{ scheduled_start: string; scheduled_end: string }>({
  scheduled_start: '',
  scheduled_end: '',
})
const whitelistDraft = ref('')

const savingSwitch = ref(false)
const savingMessage = ref(false)
const savingSchedule = ref(false)
const addingIp = ref(false)
const removingIp = ref<string | null>(null)

/** 后端对不带时区偏移的时间按 UTC 解释，这里标出浏览器时区，减少歧义 */
const timezone = localTimeZone()

/** 访客视角是否处于维护（= 当前请求 IP 的 status.active） */
const maintenanceActive = computed(() => status.value?.active === true)

/** el-table 需要对象行，这里把字符串白名单映射成 {ip} */
const whitelistRows = computed(() => (config.value?.whitelist_ips ?? []).map((ip) => ({ip})))

const hasSchedule = computed(() => Boolean(config.value?.scheduled_start || config.value?.scheduled_end))

function syncDraftFromConfig(cfg: MaintenanceConfig): void {
  messageDraft.value = cfg.message
  scheduleForm.scheduled_start = cfg.scheduled_start ?? ''
  scheduleForm.scheduled_end = cfg.scheduled_end ?? ''
}

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    const [cfg, st] = await Promise.all([maintenanceApi.getConfig(), maintenanceApi.status()])
    config.value = cfg
    status.value = st
    syncDraftFromConfig(cfg)
  } catch {
    // 失败提示由 request 层统一弹出
    failed.value = true
  } finally {
    loading.value = false
  }
}

/** 只刷新预览用的公开状态（不动草稿） */
async function refreshStatus(): Promise<void> {
  try {
    status.value = await maintenanceApi.status()
  } catch {
    // 忽略：request 层已提示
  }
}

/** 写操作返回合并后的配置：更新配置、同步草稿，并刷新预览 */
async function applyConfig(next: MaintenanceConfig): Promise<void> {
  config.value = next
  syncDraftFromConfig(next)
  await refreshStatus()
}

async function onSwitchChange(next: boolean | string | number): Promise<void> {
  const turnOn = next === true
  try {
    await ElMessageBox.confirm(
      t(turnOn ? 'admin.system.maintenance.enableConfirm' : 'admin.system.maintenance.disableConfirm'),
      t('admin.common.notice'),
      {type: 'warning'},
    )
  } catch {
    // 取消：开关是受控的（model-value 绑定 config），视觉状态不会改变
    return
  }
  savingSwitch.value = true
  try {
    const cfg = turnOn ? await maintenanceApi.enable() : await maintenanceApi.disable()
    ElMessage.success(
      t(turnOn ? 'admin.system.maintenance.switcherEnabled' : 'admin.system.maintenance.switcherDisabled'),
    )
    await applyConfig(cfg)
  } finally {
    savingSwitch.value = false
  }
}

async function saveMessage(): Promise<void> {
  const message = messageDraft.value.trim()
  if (!message) {
    ElMessage.warning(t('admin.system.maintenance.messageRequired'))
    return
  }
  savingMessage.value = true
  try {
    const cfg = await maintenanceApi.updateMessage(message)
    ElMessage.success(t('admin.system.maintenance.saved'))
    await applyConfig(cfg)
  } finally {
    savingMessage.value = false
  }
}

async function saveSchedule(): Promise<void> {
  const start = scheduleForm.scheduled_start
  const end = scheduleForm.scheduled_end
  if (!start || !end) {
    ElMessage.warning(t('admin.system.maintenance.scheduleRequired'))
    return
  }
  if (new Date(end).getTime() <= new Date(start).getTime()) {
    ElMessage.warning(t('admin.system.maintenance.scheduleInvalid'))
    return
  }
  savingSchedule.value = true
  try {
    const cfg = await maintenanceApi.schedule({scheduled_start: start, scheduled_end: end})
    ElMessage.success(t('admin.system.maintenance.saved'))
    await applyConfig(cfg)
  } finally {
    savingSchedule.value = false
  }
}

async function clearSchedule(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      t('admin.system.maintenance.clearScheduleConfirm'),
      t('admin.common.notice'),
      {type: 'warning'},
    )
  } catch {
    return
  }
  // 后端 save_config 允许 scheduled_start / scheduled_end 传 null 覆盖为「未设置」
  const cfg = await maintenanceApi.saveConfig({scheduled_start: null, scheduled_end: null})
  ElMessage.success(t('admin.system.maintenance.saved'))
  await applyConfig(cfg)
}

async function addWhitelistIp(): Promise<void> {
  const ip = whitelistDraft.value.trim()
  if (!ip) {
    ElMessage.warning(t('admin.system.maintenance.whitelistRequired'))
    return
  }
  addingIp.value = true
  try {
    const cfg = await maintenanceApi.addWhitelist(ip)
    ElMessage.success(t('admin.system.maintenance.whitelistAdded'))
    whitelistDraft.value = ''
    await applyConfig(cfg)
  } finally {
    addingIp.value = false
  }
}

async function removeWhitelistIp(ip: string): Promise<void> {
  try {
    await ElMessageBox.confirm(
      t('admin.system.maintenance.removeWhitelistConfirm', {ip}),
      t('admin.common.notice'),
      {type: 'warning'},
    )
  } catch {
    return
  }
  removingIp.value = ip
  try {
    const cfg = await maintenanceApi.removeWhitelist(ip)
    ElMessage.success(t('admin.system.maintenance.whitelistRemoved'))
    await applyConfig(cfg)
  } finally {
    removingIp.value = null
  }
}

onMounted(load)
</script>

<template>
  <AdminPage :desc="$t('admin.system.maintenance.desc')" :title="$t('admin.system.maintenance.title')">
    <template #actions>
      <el-button :icon="Refresh" :loading="loading" @click="load">
        {{ $t('admin.common.refresh') }}
      </el-button>
    </template>

    <el-alert
      v-if="failed"
      :closable="false"
      :title="$t('admin.common.loadFailed')"
      class="mb-3"
      show-icon
      type="error"
    />

    <!-- 当前状态 -->
    <section class="mcard mb-3">
      <div class="mcard__head">
        <span class="mcard__title">{{ $t('admin.system.maintenance.statusSection') }}</span>
        <el-tag :type="maintenanceActive ? 'danger' : 'success'" effect="dark" size="small">
          {{
            maintenanceActive
              ? $t('admin.system.maintenance.activeLabel')
              : $t('admin.system.maintenance.inactiveLabel')
          }}
        </el-tag>
      </div>
      <div class="mgrid">
        <div class="mgrid__item">
          <span class="mgrid__label">{{ $t('admin.system.maintenance.manualSwitch') }}</span>
          <span class="mgrid__value">
            {{ config?.enabled ? $t('admin.common.enabled') : $t('admin.common.disabled') }}
          </span>
        </div>
        <div class="mgrid__item">
          <span class="mgrid__label">{{ $t('admin.system.maintenance.inSchedule') }}</span>
          <span class="mgrid__value">
            {{ status?.in_schedule ? $t('admin.common.yes') : $t('admin.common.no') }}
          </span>
        </div>
        <div class="mgrid__item">
          <span class="mgrid__label">{{ $t('admin.system.maintenance.whitelisted') }}</span>
          <span class="mgrid__value">
            {{ status?.whitelisted ? $t('admin.common.yes') : $t('admin.common.no') }}
          </span>
        </div>
        <div class="mgrid__item">
          <span class="mgrid__label">{{ $t('admin.system.maintenance.retryAfterLabel') }}</span>
          <span class="mgrid__value">{{ config?.retry_after ?? '-' }}</span>
        </div>
        <div class="mgrid__item mgrid__item--wide">
          <span class="mgrid__label">{{ $t('admin.system.maintenance.scheduledWindow') }}</span>
          <span class="mgrid__value">
            {{ formatDateTime(config?.scheduled_start) }} → {{ formatDateTime(config?.scheduled_end) }}
          </span>
        </div>
        <div class="mgrid__item mgrid__item--wide">
          <span class="mgrid__label">{{ $t('admin.system.maintenance.checkedAt') }}</span>
          <span class="mgrid__value">{{ formatDateTime(status?.checked_at) }}</span>
        </div>
      </div>
    </section>

    <!-- 维护模式开关 -->
    <section class="mcard mb-3">
      <div class="mcard__head">
        <span class="mcard__title">{{ $t('admin.system.maintenance.switchSection') }}</span>
      </div>
      <p class="hint mb-2">{{ $t('admin.system.maintenance.switchHint') }}</p>
      <el-switch
        v-auth="'module_system:setting:edit'"
        :active-text="$t('admin.common.enabled')"
        :inactive-text="$t('admin.common.disabled')"
        :loading="savingSwitch"
        :model-value="config?.enabled ?? false"
        @change="onSwitchChange"
      />
    </section>

    <!-- 维护提示语 -->
    <section class="mcard mb-3">
      <div class="mcard__head">
        <span class="mcard__title">{{ $t('admin.system.maintenance.messageLabel') }}</span>
      </div>
      <p class="hint mb-2">{{ $t('admin.system.maintenance.messageHint') }}</p>
      <el-input
        v-model="messageDraft"
        :maxlength="500"
        :placeholder="$t('admin.system.maintenance.messagePlaceholder')"
        :rows="3"
        show-word-limit
        type="textarea"
      />
      <div class="actions-row">
        <el-button
          v-auth="'module_system:setting:edit'"
          :loading="savingMessage"
          type="primary"
          @click="saveMessage"
        >
          {{ $t('admin.system.maintenance.saveMessage') }}
        </el-button>
      </div>
    </section>

    <!-- 定时维护窗口 -->
    <section class="mcard mb-3">
      <div class="mcard__head">
        <span class="mcard__title">{{ $t('admin.system.maintenance.scheduleSection') }}</span>
      </div>
      <p class="hint mb-2">{{ $t('admin.system.maintenance.scheduleHint') }}</p>
      <el-form :model="scheduleForm" label-width="110px">
        <el-form-item :label="$t('admin.system.maintenance.scheduleStart')">
          <el-date-picker
            v-model="scheduleForm.scheduled_start"
            style="width: 100%"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.system.maintenance.scheduleEnd')">
          <el-date-picker
            v-model="scheduleForm.scheduled_end"
            style="width: 100%"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-form-item>
      </el-form>
      <p class="hint mb-2">{{ $t('admin.system.maintenance.timezoneHint', {tz: timezone}) }}</p>
      <div class="actions-row">
        <el-button
          v-auth="'module_system:setting:edit'"
          :loading="savingSchedule"
          type="primary"
          @click="saveSchedule"
        >
          {{ $t('admin.system.maintenance.saveSchedule') }}
        </el-button>
        <el-button
          v-auth="'module_system:setting:edit'"
          :disabled="!hasSchedule"
          @click="clearSchedule"
        >
          {{ $t('admin.system.maintenance.clearSchedule') }}
        </el-button>
      </div>
    </section>

    <!-- IP 白名单 -->
    <section class="mcard mb-3">
      <div class="mcard__head">
        <span class="mcard__title">{{ $t('admin.system.maintenance.whitelistSection') }}</span>
      </div>
      <p class="hint mb-2">{{ $t('admin.system.maintenance.whitelistHint') }}</p>
      <div class="whitelist-add">
        <el-input
          v-model="whitelistDraft"
          :placeholder="$t('admin.system.maintenance.whitelistPlaceholder')"
          style="max-width: 260px"
          @keyup.enter="addWhitelistIp"
        />
        <el-button
          v-auth="'module_system:setting:edit'"
          :icon="Plus"
          :loading="addingIp"
          type="primary"
          @click="addWhitelistIp"
        >
          {{ $t('admin.system.maintenance.addWhitelist') }}
        </el-button>
      </div>

      <el-table v-if="whitelistRows.length" :data="whitelistRows" border class="mt-3" size="small">
        <el-table-column :label="$t('admin.system.maintenance.whitelistIp')" prop="ip"/>
        <el-table-column :label="$t('admin.common.actions')" width="140">
          <template #default="{ row }">
            <el-button
              v-auth="'module_system:setting:edit'"
              :icon="Delete"
              :loading="removingIp === row.ip"
              link
              type="danger"
              @click="removeWhitelistIp(row.ip)"
            >
              {{ $t('admin.system.maintenance.removeWhitelist') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else :description="$t('admin.system.maintenance.whitelistEmpty')" :image-size="60"/>
    </section>

    <!-- 以匿名访客视角预览 -->
    <section class="mcard">
      <div class="mcard__head">
        <span class="mcard__title">{{ $t('admin.system.maintenance.previewSection') }}</span>
        <el-button :icon="Refresh" link type="primary" @click="refreshStatus">
          {{ $t('admin.common.refresh') }}
        </el-button>
      </div>
      <p class="hint mb-2">{{ $t('admin.system.maintenance.previewHint') }}</p>
      <el-alert
        :closable="false"
        :title="maintenanceActive
          ? $t('admin.system.maintenance.previewActive')
          : $t('admin.system.maintenance.previewInactive')"
        :type="maintenanceActive ? 'warning' : 'success'"
        show-icon
      />
      <p v-if="maintenanceActive" class="preview-message">{{ status?.message }}</p>
    </section>
  </AdminPage>
</template>

<style scoped>
.mcard {
  padding: 16px 18px;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-line, #e5e7eb);
  border-radius: 8px;
}

.mcard__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.mcard__title {
  font-size: 15px;
  font-weight: 600;
}

.mgrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px 20px;
}

.mgrid__item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mgrid__item--wide {
  grid-column: 1 / -1;
}

.mgrid__label {
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.mgrid__value {
  font-size: 14px;
  color: var(--color-fg, #303133);
  word-break: break-all;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.actions-row {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.whitelist-add {
  display: flex;
  gap: 10px;
}

.preview-message {
  margin: 10px 0 0;
  padding: 8px 12px;
  font-size: 13px;
  color: var(--color-fg-muted, #606266);
  background: var(--color-surface-soft, #f5f7fa);
  border-radius: 4px;
}

.mb-2 {
  margin-bottom: 8px;
}

.mb-3 {
  margin-bottom: 16px;
}

.mt-3 {
  margin-top: 16px;
}
</style>
