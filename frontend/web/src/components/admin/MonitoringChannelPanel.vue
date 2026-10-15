<script lang="ts" setup>
/**
 * 监控中心 · 告警推送渠道面板
 *
 * 从 `pages/system/monitoring.vue` 的「告警推送渠道」标签页抽出：渠道列表
 * （过滤 / 分页 / 测试 / 编辑 / 删除）与新建 / 编辑抽屉（原页面把抽屉放在
 * `</el-tabs>` 之外，但触发它的按钮就在本标签页的工具栏里，跟着一起搬过来）。
 *
 * 领域知识（照搬，勿丢）：`bot_token` **只入不出** —— 编辑时留空即保持原值，
 * 与后端 update 约定一致，故 `buildChannelPayload` 只在填了新 token 时才下发。
 *
 * 加载时机与原实现一致：渠道列表由 `useAdminList` 挂载即加载。
 */
import {Delete, Plus, Promotion} from '@element-plus/icons-vue'
import {reactive, ref} from 'vue'

import type {AlertChannelItem, AlertChannelPayload, AlertPlatform,} from '@/api'
import {monitoringApi} from '@/api'
import type {PageQuery} from '@/api/types'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {useAdminList} from '@/composables/useAdminList'

const {t} = useI18n()

const PLATFORMS: AlertPlatform[] = ['telegram', 'discord', 'slack', 'webhook', 'email']

const channelState = useAdminList<AlertChannelItem, PageQuery & { platform?: string; is_active?: boolean }>({
  fetcher: (params) => monitoringApi.listAlertChannels(params),
  defaultQuery: {platform: '', is_active: undefined},
})

const channelList = channelState.rows
const channelLoading = channelState.loading
const channelFailed = channelState.failed
const channelTotal = channelState.total
const channelPage = channelState.page
const channelPageSize = channelState.pageSize
const channelQuery = channelState.query
const channelSearch = channelState.search
const channelReset = channelState.reset
const channelLoad = channelState.reload
const onChannelPageChange = channelState.onPageChange
const onChannelSizeChange = channelState.onSizeChange

const channelFormVisible = ref(false)
const channelSaving = ref(false)
const channelEditingId = ref<number | null>(null)
const channelForm = reactive({
  platform: 'telegram' as string,
  webhook_url: '',
  bot_token: '',
  channel_id: '',
  enable_new_article_notification: false,
  enable_comment_notification: false,
  enable_system_alert: true,
  notification_template: '',
  is_active: true,
})

function openChannelCreate() {
  Object.assign(channelForm, {
    platform: 'telegram',
    webhook_url: '',
    bot_token: '',
    channel_id: '',
    enable_new_article_notification: false,
    enable_comment_notification: false,
    enable_system_alert: true,
    notification_template: '',
    is_active: true,
  })
  channelEditingId.value = null
  channelFormVisible.value = true
}

function openChannelEdit(row: AlertChannelItem) {
  Object.assign(channelForm, {
    platform: row.platform || 'telegram',
    webhook_url: row.webhook_url || '',
    // bot_token 永不回显：留空即表示保持原值（与后端 update 约定一致）
    bot_token: '',
    channel_id: row.channel_id || '',
    enable_new_article_notification: row.enable_new_article_notification,
    enable_comment_notification: row.enable_comment_notification,
    enable_system_alert: row.enable_system_alert,
    notification_template: row.notification_template || '',
    is_active: row.is_active,
  })
  channelEditingId.value = row.id
  channelFormVisible.value = true
}

function buildChannelPayload(): AlertChannelPayload {
  const payload: AlertChannelPayload = {
    platform: channelForm.platform,
    webhook_url: channelForm.webhook_url.trim() || null,
    channel_id: channelForm.channel_id.trim() || null,
    enable_new_article_notification: channelForm.enable_new_article_notification,
    enable_comment_notification: channelForm.enable_comment_notification,
    enable_system_alert: channelForm.enable_system_alert,
    notification_template: channelForm.notification_template.trim() || null,
    is_active: channelForm.is_active,
  }
  // 仅当用户填了新 token 才下发；留空代表保持原值（后端 update 同语义）
  if (channelForm.bot_token.trim()) payload.bot_token = channelForm.bot_token.trim()
  return payload
}

async function submitChannel() {
  if (!channelForm.platform.trim()) {
    ElMessage.warning(t('admin.system.monitoring.channelRequired'))
    return
  }
  channelSaving.value = true
  try {
    if (channelEditingId.value === null) {
      await monitoringApi.createAlertChannel(buildChannelPayload())
    } else {
      await monitoringApi.updateAlertChannel(channelEditingId.value, buildChannelPayload())
    }
    ElMessage.success(t('admin.common.save'))
    channelFormVisible.value = false
    await channelLoad()
  } finally {
    channelSaving.value = false
  }
}

async function onTestChannel(row: AlertChannelItem) {
  const result = await monitoringApi.testAlertChannel(row.id)
  if (result.sent) {
    ElMessage.success(t('admin.system.monitoring.channelTestSent'))
  } else {
    ElMessage.warning(
      `${t('admin.system.monitoring.channelTestFailed')}：${result.status_code ?? '-'} ${result.detail || ''}`,
    )
  }
}

async function onDeleteChannel(row: AlertChannelItem) {
  await ElMessageBox.confirm(
    t('admin.system.monitoring.channelDeleteConfirm', {name: row.channel_id || row.platform || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await monitoringApi.removeAlertChannel(row.id)
  ElMessage.success(t('admin.common.delete'))
  await channelLoad()
}
</script>

<template>
  <AdminListShell
    :failed="channelFailed"
    :loading="channelLoading"
    :page="channelPage"
    :page-size="channelPageSize"
    :rows="channelList"
    :selectable="false"
    :total="channelTotal"
    @refresh="channelLoad"
    @reset="channelReset"
    @search="channelSearch"
    @page-change="onChannelPageChange"
    @size-change="onChannelSizeChange"
  >
    <template #filters>
      <el-form-item :label="$t('admin.system.monitoring.channelPlatform')">
        <el-select v-model="channelQuery.platform" clearable style="width: 160px">
          <el-option v-for="item in PLATFORMS" :key="item" :label="item" :value="item"/>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('admin.system.monitoring.channelActive')">
        <el-select v-model="channelQuery.is_active" clearable style="width: 120px">
          <el-option :label="$t('admin.common.yes')" :value="true"/>
          <el-option :label="$t('admin.common.no')" :value="false"/>
        </el-select>
      </el-form-item>
    </template>

    <template #actions>
      <el-button v-auth="'module_system:monitor:manage'" :icon="Plus" type="primary"
                 @click="openChannelCreate">
        {{ $t('admin.system.monitoring.channelCreate') }}
      </el-button>
    </template>

    <el-table-column :label="$t('admin.system.monitoring.channelPlatform')" prop="platform"
                     width="120"/>
    <el-table-column :label="$t('admin.system.monitoring.channelChatId')" min-width="160"
                     prop="channel_id" show-overflow-tooltip/>
    <el-table-column :label="$t('admin.system.monitoring.channelWebhookUrl')" min-width="220"
                     prop="webhook_url" show-overflow-tooltip/>
    <el-table-column :label="$t('admin.system.monitoring.channelHasToken')" align="center" width="120">
      <template #default="{ row }">
        <el-tag :type="(row as AlertChannelItem).has_token ? 'success' : 'info'" size="small">
          {{ (row as AlertChannelItem).has_token ? $t('admin.common.yes') : $t('admin.common.no') }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column :label="$t('admin.system.monitoring.channelEnableSystemAlert')" align="center"
                     width="140">
      <template #default="{ row }">
        <el-tag :type="(row as AlertChannelItem).enable_system_alert ? 'success' : 'info'" size="small">
          {{ (row as AlertChannelItem).enable_system_alert ? $t('admin.common.yes') : $t('admin.common.no') }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column :label="$t('admin.system.monitoring.channelActive')" align="center" width="100">
      <template #default="{ row }">
        <el-tag :type="(row as AlertChannelItem).is_active ? 'success' : 'info'" size="small">
          {{ (row as AlertChannelItem).is_active ? $t('admin.common.yes') : $t('admin.common.no') }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column :label="$t('admin.common.actions')" fixed="right" width="220">
      <template #default="{ row }">
        <el-button v-auth="'module_system:monitor:manage'" :icon="Promotion" link type="primary"
                   @click="onTestChannel(row as AlertChannelItem)">
          {{ $t('admin.system.monitoring.channelTest') }}
        </el-button>
        <el-button v-auth="'module_system:monitor:manage'" link type="success"
                   @click="openChannelEdit(row as AlertChannelItem)">
          {{ $t('admin.common.edit') }}
        </el-button>
        <el-button v-auth="'module_system:monitor:manage'" :icon="Delete" link type="danger"
                   @click="onDeleteChannel(row as AlertChannelItem)">
          {{ $t('admin.common.delete') }}
        </el-button>
      </template>
    </el-table-column>
  </AdminListShell>

  <el-drawer v-model="channelFormVisible"
             :title="channelEditingId === null
               ? $t('admin.system.monitoring.channelCreate')
               : $t('admin.system.monitoring.channelEdit')"
             destroy-on-close size="480px">
    <el-form :model="channelForm" label-width="150px">
      <el-form-item :label="$t('admin.system.monitoring.channelPlatform')" required>
        <el-select v-model="channelForm.platform" style="width: 100%">
          <el-option v-for="item in PLATFORMS" :key="item" :label="item" :value="item"/>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('admin.system.monitoring.channelWebhookUrl')">
        <el-input v-model="channelForm.webhook_url"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.monitoring.channelBotToken')">
        <el-input v-model="channelForm.bot_token" show-password type="password"/>
        <div class="stats-card__label mt-3">{{ $t('admin.system.monitoring.channelBotTokenHint') }}</div>
      </el-form-item>
      <el-form-item :label="$t('admin.system.monitoring.channelChatId')">
        <el-input v-model="channelForm.channel_id"/>
        <div class="stats-card__label mt-3">{{ $t('admin.system.monitoring.channelChatIdHint') }}</div>
      </el-form-item>
      <el-form-item :label="$t('admin.system.monitoring.channelTemplate')">
        <el-input v-model="channelForm.notification_template"
                  :autosize="{minRows: 2, maxRows: 6}" type="textarea"/>
        <div class="stats-card__label mt-3">{{ $t('admin.system.monitoring.channelTemplateHint') }}</div>
      </el-form-item>
      <el-form-item :label="$t('admin.system.monitoring.channelEnableSystemAlert')">
        <el-switch v-model="channelForm.enable_system_alert"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.monitoring.channelEnableNewArticle')">
        <el-switch v-model="channelForm.enable_new_article_notification"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.monitoring.channelEnableComment')">
        <el-switch v-model="channelForm.enable_comment_notification"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.monitoring.channelActive')">
        <el-switch v-model="channelForm.is_active"/>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="channelFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
      <el-button :loading="channelSaving" type="primary" @click="submitChannel">
        {{ $t('admin.common.save') }}
      </el-button>
    </template>
  </el-drawer>
</template>

<style scoped>
.mt-3 {
  margin-top: 12px;
}

.stats-card__label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
