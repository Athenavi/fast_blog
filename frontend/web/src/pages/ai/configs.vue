<script lang="ts" setup>
/**
 * AI 配置管理（T5-11 批次 4）
 *
 * 对齐 v3 `/ai/config`：跨用户管理 AI 提供商配置。
 * api_key 只写不读（响应只有 has_api_key），更新时留空保持原值。
 */
import {Connection, Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {aiApi, type AiConfigItem, type AiConfigTestResult, type AiProviderItem,} from '@/api'
import type {PageQuery} from '@/api/types'
import {useTable} from '@/hooks/useTable'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ai.configTitle',
  permission: 'module_ai:config:view',
})

const {t} = useI18n()

interface AiConfigQueryForm extends PageQuery {
  user_id?: number
  provider?: string
  is_active?: boolean
}

const {
  list,
  loading,
  total,
  page,
  pageSize,
  query,
  search,
  reset,
  load,
  onPageChange,
  onSizeChange,
} = useTable<AiConfigItem, AiConfigQueryForm>({
  fetcher: (params) => aiApi.listConfigs(params),
  defaultQuery: {provider: '', is_active: undefined},
  syncUrl: true,
})

// ---- 新建 / 编辑 ----
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive<{
  user_id: number | undefined;
  name: string;
  api_url: string;
  api_key: string;
  model: string;
  provider: string;
  api_version: string;
  extra_headers_text: string;
  max_tokens: number;
  is_active: boolean;
  sort_order: number
}>({
  user_id: undefined,
  name: '',
  api_url: '',
  api_key: '',
  model: '',
  provider: 'openai',
  api_version: '',
  extra_headers_text: '',
  max_tokens: 1024,
  is_active: false,
  sort_order: 0,
})

const formTitle = computed(() => (editingId.value ? t('admin.ai.editConfig') : t('admin.ai.createConfig')))

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    user_id: undefined, name: '', api_url: '', api_key: '', model: '',
    provider: 'openai', api_version: '', extra_headers_text: '', max_tokens: 1024,
    is_active: false, sort_order: 0,
  })
  formVisible.value = true
}

function openEdit(row: AiConfigItem) {
  editingId.value = row.id
  Object.assign(form, {
    user_id: row.user_id,
    name: row.name || '',
    api_url: row.api_url || '',
    api_key: '', // 脱敏字段不回填，留空保持原值
    model: row.model || '',
    provider: row.provider || 'openai',
    api_version: row.api_version || '',
    extra_headers_text: row.extra_headers ? JSON.stringify(row.extra_headers, null, 2) : '',
    max_tokens: row.max_tokens || 1024,
    is_active: row.is_active,
    sort_order: row.sort_order,
  })
  formVisible.value = true
}

/** 自定义请求头：允许留空；填了必须是 JSON 对象 */
function parseExtraHeaders(): Record<string, unknown> | null | undefined {
  const text = form.extra_headers_text.trim()
  if (!text) return undefined
  try {
    const parsed = JSON.parse(text)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      ElMessage.warning(t('admin.ai.extraHeadersInvalid'))
      return null
    }
    return parsed as Record<string, unknown>
  } catch {
    ElMessage.warning(t('admin.ai.extraHeadersInvalid'))
    return null
  }
}

async function submitForm() {
  if (!form.user_id || !form.name.trim() || !form.api_url.trim() || !form.model.trim()) {
    ElMessage.warning(t('admin.ai.configRequired'))
    return
  }
  if (!editingId.value && !form.api_key) {
    ElMessage.warning(t('admin.ai.apiKeyRequired'))
    return
  }
  const extraHeaders = parseExtraHeaders()
  if (extraHeaders === null) return // 提示已在解析函数里给出

  const shared = {
    name: form.name.trim(),
    api_url: form.api_url.trim(),
    model: form.model.trim(),
    provider: form.provider || 'openai',
    api_version: form.api_version.trim() || null,
    extra_headers: extraHeaders ?? null,
    max_tokens: form.max_tokens || 1024,
    is_active: form.is_active,
    sort_order: form.sort_order,
  }
  saving.value = true
  try {
    if (editingId.value) {
      await aiApi.updateConfig(editingId.value, {...shared, api_key: form.api_key || undefined})
    } else {
      await aiApi.createConfig({...shared, user_id: form.user_id, api_key: form.api_key})
    }
    ElMessage.success(t('admin.common.save'))
    formVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

// ---- 支持的 provider（与后端协议表一致）----
const providers = ref<AiProviderItem[]>([])

async function loadProviders(): Promise<void> {
  try {
    providers.value = await aiApi.listProviders()
  } catch {
    providers.value = []
  }
}

// ---- 测试连接（真实调用一次模型）----
const testVisible = ref(false)
const testLoadingId = ref<number | null>(null)
const testResult = ref<AiConfigTestResult | null>(null)

async function onTest(row: AiConfigItem): Promise<void> {
  testLoadingId.value = row.id
  testResult.value = null
  try {
    testResult.value = await aiApi.testConfig(row.id)
    testVisible.value = true
  } finally {
    testLoadingId.value = null
  }
}

onMounted(loadProviders)

async function onDelete(row: AiConfigItem) {
  await ElMessageBox.confirm(t('admin.ai.deleteConfigConfirm'), t('admin.common.notice'), {type: 'warning'})
  await aiApi.removeConfig(row.id)
  ElMessage.success(t('admin.common.delete'))
  await load()
}
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <!-- 搜索区 -->
      <el-form :inline="true" :model="query" @submit.prevent="search()">
        <el-form-item :label="$t('admin.ai.userId')">
          <el-input-number v-model="query.user_id" :min="1" controls-position="right" style="width: 130px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ai.provider')">
          <el-input
            v-model="query.provider"
            :placeholder="$t('admin.ai.providerPlaceholder')"
            clearable
            style="width: 140px"
            @keyup.enter="search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="query.is_active" :placeholder="$t('admin.common.all')" clearable style="width: 110px">
            <el-option :label="$t('admin.system.sensitiveWord.active')" :value="true"/>
            <el-option :label="$t('admin.system.sensitiveWord.inactive')" :value="false"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="search()">{{ $t('admin.common.search') }}</el-button>
          <el-button :icon="Refresh" @click="reset()">{{ $t('admin.common.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <!-- 操作区 -->
      <div class="table-toolbar">
        <el-button v-auth="'module_ai:config:create'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.ai.createConfig') }}
        </el-button>
        <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: total}) }}</span>
      </div>

      <!-- 表格 -->
      <AdminTableSkeleton v-if="loading && !list.length" :rows="5"/>

      <AdminEmpty v-else-if="!loading && !list.length" :title="$t('admin.common.empty')"/>
      <el-table v-else v-loading="loading" :data="list" border stripe>
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column :label="$t('admin.ai.userId')" prop="user_id" width="90"/>
        <el-table-column :label="$t('admin.common.name')" min-width="130" prop="name" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.ai.provider')" prop="provider" width="100"/>
        <el-table-column :label="$t('admin.ai.model')" min-width="130" prop="model" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.ai.apiUrl')" min-width="180" prop="api_url" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.ai.hasApiKey')" width="110">
          <template #default="{ row }">
            <el-tag :type="(row as AiConfigItem).has_api_key ? 'success' : 'info'" size="small">
              {{ (row as AiConfigItem).has_api_key ? $t('admin.common.yes') : $t('admin.common.no') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.status')" width="90">
          <template #default="{ row }">
            <el-tag :type="(row as AiConfigItem).is_active ? 'success' : 'info'" size="small">
              {{
                (row as AiConfigItem).is_active ? $t('admin.system.sensitiveWord.active') : $t('admin.system.sensitiveWord.inactive')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="230">
          <template #default="{ row }">
            <el-button
              v-auth="'module_ai:config:edit'"
              :icon="Connection"
              :loading="testLoadingId === (row as AiConfigItem).id"
              link
              type="success"
              @click="onTest(row as AiConfigItem)"
            >
              {{ $t('admin.ai.testConnection') }}
            </el-button>
            <el-button v-auth="'module_ai:config:edit'" link type="primary"
                       @click="openEdit(row as AiConfigItem)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button v-auth="'module_ai:config:delete'" link type="danger"
                       @click="onDelete(row as AiConfigItem)">
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        background
        class="table-pagination"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </el-card>

    <!-- 新建 / 编辑 -->
    <el-drawer v-model="formVisible" :title="formTitle" destroy-on-close size="500px">
      <el-form :model="form" label-width="110px">
        <el-form-item :label="$t('admin.ai.userId')" required>
          <el-input-number v-model="form.user_id" :min="1" controls-position="right" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="form.name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ai.provider')">
          <el-select v-model="form.provider" style="width: 100%">
            <el-option
              v-for="item in providers"
              :key="item.provider"
              :label="`${item.provider} · ${item.protocol}`"
              :value="item.provider"
            />
            <el-option v-if="!providers.length" label="openai" value="openai"/>
          </el-select>
          <div class="form-hint">{{ $t('admin.ai.providerHint') }}</div>
        </el-form-item>
        <el-form-item :label="$t('admin.ai.apiUrl')" required>
          <el-input v-model="form.api_url" placeholder="https://api.openai.com/v1"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ai.model')" required>
          <el-input v-model="form.model" placeholder="gpt-4o"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ai.apiKey')" :required="!editingId">
          <el-input
            v-model="form.api_key"
            :placeholder="editingId ? $t('admin.ai.apiKeyKeepHint') : 'sk-...'"
            show-password
            type="password"
          />
          <div class="form-hint">{{ $t('admin.ai.apiKeyEncryptHint') }}</div>
        </el-form-item>
        <el-form-item :label="$t('admin.ai.apiVersion')">
          <el-input v-model="form.api_version" :placeholder="$t('admin.ai.apiVersionPlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ai.maxTokens')">
          <el-input-number v-model="form.max_tokens" :max="128000" :min="1" controls-position="right"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ai.extraHeaders')">
          <el-input
            v-model="form.extra_headers_text"
            :autosize="{minRows: 2, maxRows: 6}"
            :placeholder="$t('admin.ai.extraHeadersPlaceholder')"
            type="textarea"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.sortOrder')">
          <el-input-number v-model="form.sort_order" :min="0" controls-position="right"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="form.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-drawer>

    <!-- 连接测试结果（后端真实调用了一次模型） -->
    <el-dialog v-model="testVisible" :title="$t('admin.ai.testResult')" width="560px">
      <el-descriptions v-if="testResult" :column="1" border size="small">
        <el-descriptions-item :label="$t('admin.ai.provider')">
          {{ testResult.provider }} · {{ testResult.protocol }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.ai.model')">{{ testResult.model }}</el-descriptions-item>
        <el-descriptions-item :label="$t('admin.ai.latency')">{{ testResult.latency_ms }} ms</el-descriptions-item>
        <el-descriptions-item :label="$t('admin.ai.tokensUsed')">
          {{ (testResult.usage?.prompt_tokens ?? 0) + (testResult.usage?.completion_tokens ?? 0) }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('admin.ai.reply')">
          <div class="reply">{{ testResult.reply }}</div>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<style scoped>
.form-hint {
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-secondary);
}

.reply {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
