<script lang="ts" setup>
/**
 * 邮件服务（T5-11 批次 2）
 *
 * 对齐 v3 `/ops/email`：服务配置（凭据脱敏，留空保持原值）+ 邮件订阅列表。
 * 两个列表都不带筛选条件：配置数量有限（不分页），订阅列表分页。
 */
import {Plus} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {emailApi, type EmailConfigItem, type EmailSubscriptionItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ops.email.title',
  permission: 'module_ops:email:view',
})

const {t} = useI18n()

// ---- 服务配置（接口返回数组，不分页）----
const configs = useAdminList<EmailConfigItem, PageQuery>({
  fetcher: async () => {
    const items = await emailApi.configs()
    return {items: items ?? [], total: items?.length ?? 0, page: 1, pageSize: 0, pages: 1}
  },
})

// ---- 订阅 ----
const subs = useAdminList<EmailSubscriptionItem, PageQuery>({
  fetcher: (params) => emailApi.subscriptions(params),
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
    await configs.reload()
  } finally {
    saving.value = false
  }
}

async function onDelete(row: EmailConfigItem) {
  await ElMessageBox.confirm(t('admin.ops.email.deleteConfirm'), t('admin.common.notice'), {type: 'warning'})
  await emailApi.removeConfig(row.id)
  ElMessage.success(t('admin.common.delete'))
  await configs.reload()
}
</script>

<template>
  <AdminPage :desc="$t('admin.ops.email.desc')" :title="$t('admin.ops.email.title')">
    <!-- 服务配置 -->
    <AdminListShell
      :empty-desc="$t('admin.ops.email.configEmptyDesc')"
      :empty-title="$t('admin.ops.email.configEmptyTitle')"
      :failed="configs.failed.value"
      :loading="configs.loading.value"
      :page="configs.page.value"
      :page-size="configs.pageSize.value"
      :paginate="false"
      :rows="configs.rows.value"
      :selectable="false"
      :total="configs.total.value"
      @refresh="configs.reload"
    >
      <template #actions>
        <span class="mr-2 font-medium">{{ $t('admin.ops.email.configTitle') }}</span>
        <el-button v-auth="'module_ops:email:edit'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.ops.email.createConfig') }}
        </el-button>
      </template>

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
              (row as EmailConfigItem).is_active ? $t('admin.common.enabled') : $t('admin.common.disabled')
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
    </AdminListShell>

    <!-- 邮件订阅 -->
    <AdminListShell
      :empty-desc="$t('admin.ops.email.subEmptyDesc')"
      :empty-title="$t('admin.ops.email.subEmptyTitle')"
      :failed="subs.failed.value"
      :loading="subs.loading.value"
      :page="subs.page.value"
      :page-size="subs.pageSize.value"
      :rows="subs.rows.value"
      :selectable="false"
      :total="subs.total.value"
      class="mt-4"
      @refresh="subs.reload"
      @page-change="subs.onPageChange"
    >
      <template #actions>
        <span class="mr-2 font-medium">{{ $t('admin.ops.email.subTitle') }}</span>
      </template>

      <el-table-column :label="$t('admin.marketing.vip.userId')" prop="user_id" width="110"/>
      <el-table-column :label="$t('admin.ops.email.subscribed')" width="110">
        <template #default="{ row }">
          {{ (row as EmailSubscriptionItem).subscribed ? $t('admin.common.yes') : $t('admin.common.no') }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.content.approval.createdAt')" min-width="180" prop="created_at"/>
    </AdminListShell>

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
  </AdminPage>
</template>

<style scoped>
.mr-2 {
  margin-right: 8px;
}
</style>
