<script lang="ts" setup>
/**
 * 邮件服务（T5-11 批次 2）
 *
 * 对齐 v3 `/ops/email`：服务配置（凭据脱敏，单激活）+ 订阅列表。
 */
import {Plus, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {emailApi, type EmailConfigItem} from '@/api'
import {useTable} from '@/hooks/useTable'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ops.email.title',
  permission: 'module_ops:email:view',
})

const {t} = useI18n()

const configs = ref<EmailConfigItem[]>([])
const configsLoading = ref(false)

async function loadConfigs() {
  configsLoading.value = true
  try {
    configs.value = await emailApi.configs()
  } finally {
    configsLoading.value = false
  }
}

onMounted(() => {
  loadConfigs()
})

// ---- 配置编辑 ----
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({
  provider: 'smtp', api_key: '', smtp_host: '', smtp_port: 465, smtp_username: '',
  smtp_password: '', from_email: '', from_name: '',
  enable_batch_sending: false, batch_size: 50, daily_limit: 1000, is_active: true,
})

const formTitle = computed(() =>
  editingId.value ? t('admin.ops.email.editConfig') : t('admin.ops.email.createConfig'))

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    provider: 'smtp', api_key: '', smtp_host: '', smtp_port: 465, smtp_username: '',
    smtp_password: '', from_email: '', from_name: '',
    enable_batch_sending: false, batch_size: 50, daily_limit: 1000, is_active: true,
  })
  formVisible.value = true
}

function openEdit(row: EmailConfigItem) {
  editingId.value = row.id
  Object.assign(form, {
    provider: row.provider || 'smtp',
    api_key: '',
    smtp_host: row.smtp_host || '',
    smtp_port: row.smtp_port ?? 465,
    smtp_username: row.smtp_username || '',
    smtp_password: '',
    from_email: row.from_email || '',
    from_name: row.from_name || '',
    enable_batch_sending: row.enable_batch_sending,
    batch_size: row.batch_size ?? 50,
    daily_limit: row.daily_limit ?? 1000,
    is_active: row.is_active,
  })
  formVisible.value = true
}

async function submitConfig() {
  if (!form.from_email.trim()) {
    ElMessage.warning(t('admin.ops.email.fromEmailRequired'))
    return
  }
  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      provider: form.provider,
      smtp_host: form.smtp_host || null,
      smtp_port: form.smtp_port,
      smtp_username: form.smtp_username || null,
      from_email: form.from_email.trim(),
      from_name: form.from_name || null,
      enable_batch_sending: form.enable_batch_sending,
      batch_size: form.batch_size,
      daily_limit: form.daily_limit,
      is_active: form.is_active,
    }
    // 凭据留空表示保持原值
    if (form.api_key) payload.api_key = form.api_key
    if (form.smtp_password) payload.smtp_password = form.smtp_password
    if (editingId.value) {
      await emailApi.updateConfig(editingId.value, payload)
    } else {
      await emailApi.createConfig(payload)
    }
    ElMessage.success(t('admin.common.save'))
    formVisible.value = false
    await loadConfigs()
  } finally {
    saving.value = false
  }
}

async function onDelete(row: EmailConfigItem) {
  await ElMessageBox.confirm(t('admin.ops.email.deleteConfirm'), t('admin.common.notice'), {type: 'warning'})
  await emailApi.removeConfig(row.id)
  ElMessage.success(t('admin.common.delete'))
  await loadConfigs()
}

// ---- 订阅 ----
const subTable = useTable({fetcher: (params) => emailApi.subscriptions(params)})
</script>

<template>
  <div class="page-container">
    <el-card class="mb-4" shadow="never">
      <template #header>
        <div class="flex items-center justify-between">
          <span>{{ $t('admin.ops.email.configTitle') }}</span>
          <el-button v-auth="'module_ops:email:edit'" :icon="Plus" size="small" type="primary" @click="openCreate">
            {{ $t('admin.ops.email.createConfig') }}
          </el-button>
        </div>
      </template>
      <AdminTableSkeleton v-if="configsLoading && !configs.length" :rows="5"/>

      <AdminEmpty v-else-if="!configsLoading && !configs.length" :title="$t('admin.common.empty')"/>
      <el-table v-else v-loading="configsLoading" :data="configs" border>
        <el-table-column :label="$t('admin.ops.email.provider')" prop="provider" width="110"/>
        <el-table-column :label="$t('admin.ops.email.fromEmail')" min-width="180" prop="from_email"/>
        <el-table-column :label="$t('admin.ops.email.fromName')" prop="from_name" width="140"/>
        <el-table-column :label="$t('admin.ops.email.smtpHost')" min-width="160" prop="smtp_host"/>
        <el-table-column :label="$t('admin.ops.email.hasKey')" width="110">
          <template #default="{ row }">
            {{
              (row as EmailConfigItem).has_api_key || (row as EmailConfigItem).has_smtp_password ? $t('admin.common.yes') : $t('admin.common.no')
            }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.status')" width="90">
          <template #default="{ row }">
            <el-tag :type="(row as EmailConfigItem).is_active ? 'success' : 'info'" size="small">
              {{
                (row as EmailConfigItem).is_active ? $t('admin.system.sensitiveWord.active') : $t('admin.system.sensitiveWord.inactive')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" width="150">
          <template #default="{ row }">
            <el-button v-auth="'module_ops:email:edit'" link type="primary" @click="openEdit(row as EmailConfigItem)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button v-auth="'module_ops:email:delete'" link type="danger" @click="onDelete(row as EmailConfigItem)">
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="flex items-center justify-between">
          <span>{{ $t('admin.ops.email.subTitle') }}</span>
          <el-button :icon="Refresh" size="small" @click="subTable.load()">{{ $t('admin.common.refresh') }}</el-button>
        </div>
      </template>
      <el-table v-loading="subTable.loading.value" :data="subTable.list.value" border>
        <el-table-column :label="$t('admin.marketing.vip.userId')" prop="user_id" width="110"/>
        <el-table-column :label="$t('admin.ops.email.subscribed')" width="110">
          <template #default="{ row }">
            {{ (row as { subscribed: boolean }).subscribed ? $t('admin.common.yes') : $t('admin.common.no') }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.content.approval.createdAt')" min-width="180" prop="created_at"/>
      </el-table>
      <el-pagination
        :current-page="subTable.page.value" :page-size="subTable.pageSize.value" :total="subTable.total.value"
        background class="table-pagination" layout="total, prev, pager, next"
        @current-change="subTable.onPageChange"
      />
    </el-card>

    <!-- 配置编辑 -->
    <el-drawer v-model="formVisible" :title="formTitle" destroy-on-close size="480px">
      <el-form :model="form" label-width="110px">
        <el-form-item :label="$t('admin.ops.email.provider')">
          <el-select v-model="form.provider" style="width: 100%">
            <el-option label="SMTP" value="smtp"/>
            <el-option label="SendGrid" value="sendgrid"/>
            <el-option label="Mailgun" value="mailgun"/>
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.provider !== 'smtp'" :label="$t('admin.ops.email.apiKey')">
          <el-input v-model="form.api_key" :placeholder="editingId ? $t('admin.ops.email.keepSecret') : ''"
                    show-password/>
        </el-form-item>
        <template v-if="form.provider === 'smtp'">
          <el-form-item :label="$t('admin.ops.email.smtpHost')">
            <el-input v-model="form.smtp_host"/>
          </el-form-item>
          <el-form-item :label="$t('admin.ops.email.smtpPort')">
            <el-input-number v-model="form.smtp_port" :max="65535" :min="1" style="width: 100%"/>
          </el-form-item>
          <el-form-item :label="$t('admin.ops.email.smtpUser')">
            <el-input v-model="form.smtp_username"/>
          </el-form-item>
          <el-form-item :label="$t('admin.ops.email.smtpPassword')">
            <el-input v-model="form.smtp_password" :placeholder="editingId ? $t('admin.ops.email.keepSecret') : ''"
                      show-password/>
          </el-form-item>
        </template>
        <el-form-item :label="$t('admin.ops.email.fromEmail')" required>
          <el-input v-model="form.from_email"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.email.fromName')">
          <el-input v-model="form.from_name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.email.batchSending')">
          <el-switch v-model="form.enable_batch_sending"/>
        </el-form-item>
        <el-form-item v-if="form.enable_batch_sending" :label="$t('admin.ops.email.batchSize')">
          <el-input-number v-model="form.batch_size" :min="1" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.email.dailyLimit')">
          <el-input-number v-model="form.daily_limit" :min="1" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="form.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitConfig">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-drawer>
  </div>
</template>
