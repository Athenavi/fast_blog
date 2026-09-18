<script lang="ts" setup>
/**
 * Webhook 管理
 *
 * 对齐 v3 `/ops/webhook`：列表、可用事件、创建/更新/删除、发送测试。
 * 样式统一使用 Element Plus 的 CSS 变量。
 */
import {Delete, Edit, Plus, Promotion, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from 'element-plus'
import {reactive, ref} from 'vue'

import {webhookApi, type WebhookItem, type WebhookPayload} from '@/api'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'Webhook',
  permission: 'module_ops:webhook:view',
})

const loading = ref(false)
const list = ref<WebhookItem[]>([])
const total = ref(0)
const query = reactive({page: 1, page_size: 20})

async function loadList(): Promise<void> {
  loading.value = true
  try {
    const data = await webhookApi.list()
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

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
    ElMessage.warning('请填写名称与回调地址')
    return
  }
  if (!/^https?:\/\//.test(url)) {
    ElMessage.warning('回调地址需以 http:// 或 https:// 开头')
    return
  }

  saving.value = true
  try {
    const payload: WebhookPayload = {name, url, events: form.events ?? [], is_active: form.is_active}
    if (form.secret) payload.secret = form.secret

    if (editingId.value) {
      await webhookApi.update(editingId.value, payload)
      ElMessage.success('已保存')
    } else {
      await webhookApi.create(payload)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    await loadList()
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------- 操作
async function testHook(row: WebhookItem): Promise<void> {
  await ElMessageBox.confirm(`向「${row.name}」发送一条测试事件？`, '提示', {type: 'info'})
  const result = await webhookApi.test(row.id)
  if (result?.triggered) {
    ElMessage.success(`已触发：${result.event}`)
  } else {
    ElMessage.warning(result?.detail || '未触发（可能没有可用事件）')
  }
}

async function removeRow(row: WebhookItem): Promise<void> {
  await ElMessageBox.confirm(`确定删除 Webhook「${row.name}」吗？`, '提示', {type: 'warning'})
  await webhookApi.remove(row.id)
  ElMessage.success('已删除')
  await loadList()
}

onMounted(async () => {
  await Promise.all([loadList(), loadEvents()])
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="toolbar">
        <el-button v-auth="'module_ops:webhook:edit'" :icon="Plus" type="primary" @click="openCreate">
          新建 Webhook
        </el-button>
        <el-button :icon="Refresh" circle @click="loadList"/>
      </div>

      <el-table v-loading="loading" :data="list" row-key="id">
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column label="名称" min-width="140" prop="name"/>
        <el-table-column label="回调地址" min-width="260" prop="url" show-overflow-tooltip/>
        <el-table-column label="订阅事件" min-width="220">
          <template #default="{row}">
            <el-tag v-for="event in (row.events || []).slice(0, 3)" :key="event" class="mr-1" size="small">
              {{ event }}
            </el-tag>
            <span v-if="(row.events || []).length > 3" class="more">+{{ row.events.length - 3 }}</span>
            <span v-if="!(row.events || []).length" class="more">全部事件</span>
          </template>
        </el-table-column>
        <el-table-column label="密钥" width="80">
          <template #default="{row}">
            <el-tag :type="row.has_secret ? 'success' : 'info'" size="small">
              {{ row.has_secret ? '已设置' : '无' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{row}">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="170">
          <template #default="{row}">{{ formatDateTime(row.updated_at || row.created_at) }}</template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" width="200">
          <template #default="{row}">
            <el-button :icon="Promotion" link type="primary" @click="testHook(row)">测试</el-button>
            <el-button
              v-auth="'module_ops:webhook:edit'"
              :icon="Edit"
              link
              type="primary"
              @click="openEdit(row)"
            >
              编辑
            </el-button>
            <el-button
              v-auth="'module_ops:webhook:edit'"
              :icon="Delete"
              link
              type="danger"
              @click="removeRow(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        class="pagination"
        layout="total, prev, pager, next"
        @current-change="loadList"
      />
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑 Webhook' : '新建 Webhook'"
      destroy-on-close
      width="620px"
    >
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" maxlength="100" placeholder="如 同步到 CI"/>
        </el-form-item>
        <el-form-item label="回调地址" required>
          <el-input v-model="form.url" placeholder="https://example.com/hook"/>
        </el-form-item>
        <el-form-item label="订阅事件">
          <el-select
            v-model="form.events"
            allow-create
            default-first-option
            filterable
            multiple
            placeholder="留空表示订阅全部事件"
            style="width: 100%"
          >
            <el-option v-for="event in eventOptions" :key="event" :label="event" :value="event"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="editingId ? '重置密钥' : '密钥'">
          <el-input
            v-model="form.secret"
            :placeholder="editingId ? '留空表示不修改' : '用于校验请求签名'"
            show-password
            type="password"
          />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active"/>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.mr-1 {
  margin-right: 4px;
}

.more {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.pagination {
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
