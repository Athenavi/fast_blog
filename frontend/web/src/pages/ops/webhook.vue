<script lang="ts" setup>
const {t} = useI18n()
/**
 * Webhook 管理
 *
 * 对齐 v3 `/ops/webhook`：列表、可用事件、创建/更新/删除、发送测试。
 *
 * 该列表接口返回全量（不接受分页参数），原先的分页器其实没有把页码传给后端，
 * 属于"看起来能翻页"的假象；这里改用列表壳并关闭分页器，如实反映接口能力。
 */
import {Delete, Edit, Plus, Promotion} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {reactive, ref} from 'vue'

import {webhookApi, type WebhookItem, type WebhookPayload} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ops.webhook.title',
  permission: 'module_ops:webhook:view',
})

const list = useAdminList<WebhookItem, PageQuery>({
  fetcher: () => webhookApi.list(),
})

// ---------------------------------------------------------------- 事件选项
const eventOptions = ref<string[]>([])

async function loadEvents(): Promise<void> {
  try {
    const data = await webhookApi.events()
    eventOptions.value = data.map((item) => item.event)
  } catch {
    eventOptions.value = []
  }
}

// ---------------------------------------------------------------- 编辑
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)

const form = reactive<WebhookPayload>({name: '', url: '', events: [], secret: '', is_active: true})

function emptyForm(): WebhookPayload {
  return {name: '', url: '', events: [], secret: '', is_active: true}
}

function openCreate(): void {
  editingId.value = null
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEdit(row: WebhookItem): void {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name ?? '',
    url: row.url ?? '',
    events: [...(row.events ?? [])],
    // 出于安全，后端不回传密钥明文；留空表示不修改
    secret: '',
    is_active: row.is_active,
  })
  dialogVisible.value = true
}

async function submitForm(): Promise<void> {
  const name = form.name.trim()
  const url = form.url.trim()
  if (!name || !url) {
    ElMessage.warning(t('admin.ops.webhook.enterANameAndCallbackUrl'))
    return
  }
  if (!/^https?:\/\//.test(url)) {
    ElMessage.warning(t('admin.ops.webhook.callbackUrlMustStartWithHttpOrHttps'))
    return
  }

  saving.value = true
  try {
    const payload: WebhookPayload = {name, url, events: form.events ?? [], is_active: form.is_active}
    if (form.secret) payload.secret = form.secret

    if (editingId.value) {
      await webhookApi.update(editingId.value, payload)
      ElMessage.success(t('admin.ops.webhook.saved'))
    } else {
      await webhookApi.create(payload)
      ElMessage.success(t('admin.ops.webhook.created'))
    }
    dialogVisible.value = false
    await list.reload()
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------- 操作
async function testHook(row: WebhookItem): Promise<void> {
  await ElMessageBox.confirm(t('admin.ops.webhook.testConfirm', {name: row.name}), t('admin.common.notice'), {type: 'info'})
  const result = await webhookApi.test(row.id)
  if (result?.triggered) {
    ElMessage.success(t('admin.ops.webhook.triggered', {event: result.event}))
  } else {
    ElMessage.warning(result?.detail || t('admin.ops.webhook.notTriggeredNoAvailableEvent'))
  }
}

async function removeRow(row: WebhookItem): Promise<void> {
  await ElMessageBox.confirm(t('admin.ops.webhook.deleteConfirm', {name: row.name}), t('admin.common.notice'), {type: 'warning'})
  await webhookApi.remove(row.id)
  ElMessage.success(t('admin.ops.webhook.deleted'))
  await list.reload()
}

onMounted(loadEvents)
</script>

<template>
  <AdminPage :desc="$t('admin.ops.webhook.desc')" :title="$t('admin.ops.webhook.title')">
    <template #actions>
      <el-button v-auth="'module_ops:webhook:edit'" :icon="Plus" type="primary" @click="openCreate">
        {{ $t('admin.ops.webhook.createWebhook') }}
      </el-button>
    </template>

    <AdminListShell
      :empty-desc="$t('admin.ops.webhook.emptyDesc')"
      :empty-title="$t('admin.ops.webhook.emptyTitle')"
      :failed="list.failed.value"
      :loading="list.loading.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      :paginate="false"
      :rows="list.rows.value"
      :selectable="false"
      :total="list.total.value"
      @refresh="list.reload"
    >
      <el-table-column label="ID" prop="id" width="70"/>
      <el-table-column :label="$t('admin.common.name')" min-width="140" prop="name"/>
      <el-table-column :label="$t('admin.ops.webhook.callbackUrl')" min-width="260" prop="url" show-overflow-tooltip/>
      <el-table-column :label="$t('admin.ops.webhook.subscribedEvents')" min-width="220">
        <template #default="{row}">
          <el-tag v-for="event in (row.events || []).slice(0, 3)" :key="event" class="mr-1" size="small">
            {{ event }}
          </el-tag>
          <span v-if="(row.events || []).length > 3" class="more">+{{ row.events.length - 3 }}</span>
          <span v-if="!(row.events || []).length" class="more">{{ $t('admin.ops.webhook.allEvents') }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.ops.webhook.secret')" width="80">
        <template #default="{row}">
          <el-tag :type="row.has_secret ? 'success' : 'info'" size="small">
            {{ row.has_secret ? t('admin.ops.webhook.set') : t('admin.ops.webhook.none') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.status')" width="90">
        <template #default="{row}">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? t('admin.common.enabled') : t('admin.common.disabled') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.updatedAt')" width="170">
        <template #default="{row}">{{ formatDateTime(row.updated_at || row.created_at) }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="200">
        <template #default="{row}">
          <el-button :icon="Promotion" link type="primary" @click="testHook(row)">{{
              $t('admin.ops.webhook.test')
            }}
          </el-button>
          <el-button
            v-auth="'module_ops:webhook:edit'"
            :icon="Edit"
            link
            type="primary"
            @click="openEdit(row)"
          >
            {{ $t('admin.common.edit') }}
          </el-button>
          <el-button
            v-auth="'module_ops:webhook:edit'"
            :icon="Delete"
            link
            type="danger"
            @click="removeRow(row)"
          >
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? t('admin.ops.webhook.editWebhook') : t('admin.ops.webhook.createWebhook')"
      destroy-on-close
      width="620px"
    >
      <el-form :model="form" label-width="90px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="form.name" :placeholder="$t('admin.ops.webhook.eGSyncToCi')" maxlength="100"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.webhook.callbackUrl')" required>
          <el-input v-model="form.url" placeholder="https://example.com/hook"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.webhook.subscribedEvents')">
          <el-select
            v-model="form.events"
            allow-create
            default-first-option
            filterable
            multiple
            :placeholder="$t('admin.ops.webhook.leaveBlankToSubscribeToAllEvents')"
            style="width: 100%"
          >
            <el-option v-for="event in eventOptions" :key="event" :label="event" :value="event"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="editingId ? t('admin.ops.webhook.resetSecret') : t('admin.ops.webhook.secret2')">
          <el-input
            v-model="form.secret"
            :placeholder="editingId ? t('admin.ops.webhook.leaveBlankToKeepUnchanged') : t('admin.ops.webhook.usedToVerifyRequestSignatures')"
            show-password
            autocomplete="off"
            type="password"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.enabled')">
          <el-switch v-model="form.is_active"/>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>
  </AdminPage>
</template>

<style scoped>
.mr-1 {
  margin-right: 4px;
}

.more {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
