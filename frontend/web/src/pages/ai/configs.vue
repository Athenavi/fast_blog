<script lang="ts" setup>
/**
 * AI 配置管理（T5-11 批次 4）
 *
 * 对齐 v3 `/ai/config`：跨用户管理 AI 提供商配置。
 * api_key 只写不读（响应只有 has_api_key），更新时留空保持原值。
 */
import {Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {aiApi, type AiConfigItem} from '@/api'
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
  is_active: boolean;
  sort_order: number
}>({
  user_id: undefined,
  name: '',
  api_url: '',
  api_key: '',
  model: '',
  provider: 'openai',
  is_active: false,
  sort_order: 0,
})

const formTitle = computed(() => (editingId.value ? t('admin.ai.editConfig') : t('admin.ai.createConfig')))

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    user_id: undefined, name: '', api_url: '', api_key: '', model: '',
    provider: 'openai', is_active: false, sort_order: 0,
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
    is_active: row.is_active,
    sort_order: row.sort_order,
  })
  formVisible.value = true
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
  saving.value = true
  try {
    if (editingId.value) {
      await aiApi.updateConfig(editingId.value, {
        name: form.name.trim(),
        api_url: form.api_url.trim(),
        api_key: form.api_key || undefined,
        model: form.model.trim(),
        provider: form.provider || 'openai',
        is_active: form.is_active,
        sort_order: form.sort_order,
      })
    } else {
      await aiApi.createConfig({
        user_id: form.user_id,
        name: form.name.trim(),
        api_url: form.api_url.trim(),
        api_key: form.api_key,
        model: form.model.trim(),
        provider: form.provider || 'openai',
        is_active: form.is_active,
        sort_order: form.sort_order,
      })
    }
    ElMessage.success(t('admin.common.save'))
    formVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

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
      <el-table v-loading="loading" :data="list" border stripe>
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
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
          <template #default="{ row }">
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
            <el-option label="OpenAI" value="openai"/>
            <el-option label="Anthropic" value="anthropic"/>
            <el-option label="Azure" value="azure"/>
            <el-option label="DeepSeek" value="deepseek"/>
            <el-option label="Ollama" value="ollama"/>
            <el-option label="Custom" value="custom"/>
          </el-select>
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
  </div>
</template>
