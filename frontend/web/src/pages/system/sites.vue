<script lang="ts" setup>
/**
 * 多站点管理（T5-11 批次 4）
 *
 * 对齐 v3 `/system/site`：站点 CRUD。slug 创建后锁定；
 * domain 唯一；is_default 全站唯一（后端强制），默认站点不可删除。
 */
import {Plus} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {siteApi, type SiteItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useTable} from '@/hooks/useTable'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.site.title',
  permission: 'module_system:site:view',
})

const {t} = useI18n()

interface SiteQueryForm extends PageQuery {
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
} = useTable<SiteItem, SiteQueryForm>({
  fetcher: (params) => siteApi.list(params),
  defaultQuery: {is_active: undefined},
  syncUrl: true,
})

// ---- 新建 / 编辑 ----
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive<{
  name: string;
  slug: string;
  domain: string;
  additional_domains: string;
  description: string;
  theme: string;
  language: string;
  timezone: string;
  is_active: boolean;
  is_default: boolean
}>({
  name: '',
  slug: '',
  domain: '',
  additional_domains: '',
  description: '',
  theme: 'default',
  language: 'en',
  timezone: 'UTC',
  is_active: true,
  is_default: false,
})

const formTitle = computed(() => (editingId.value ? t('admin.system.site.editTitle') : t('admin.system.site.createTitle')))

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    name: '', slug: '', domain: '', additional_domains: '', description: '',
    theme: 'default', language: 'en', timezone: 'UTC', is_active: true, is_default: false,
  })
  formVisible.value = true
}

function openEdit(row: SiteItem) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name || '',
    slug: row.slug || '',
    domain: row.domain || '',
    additional_domains: (row.additional_domains || []).join(', '),
    description: row.description || '',
    theme: row.theme || 'default',
    language: row.language || 'en',
    timezone: row.timezone || 'UTC',
    is_active: row.is_active,
    is_default: row.is_default,
  })
  formVisible.value = true
}

function parseAdditionalDomains(): string[] {
  return form.additional_domains
    .split(/[,，;\s]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

async function submitForm() {
  if (!form.name.trim() || !form.domain.trim()) {
    ElMessage.warning(t('admin.system.site.required'))
    return
  }
  if (!editingId.value && !form.slug.trim()) {
    ElMessage.warning(t('admin.system.site.slugRequired'))
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      domain: form.domain.trim(),
      additional_domains: parseAdditionalDomains(),
      description: form.description || null,
      theme: form.theme || 'default',
      language: form.language || 'en',
      timezone: form.timezone || 'UTC',
      is_active: form.is_active,
      is_default: form.is_default,
    }
    if (editingId.value) {
      await siteApi.update(editingId.value, payload)
    } else {
      await siteApi.create({...payload, slug: form.slug.trim()})
    }
    ElMessage.success(t('admin.common.save'))
    formVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(row: SiteItem) {
  await ElMessageBox.confirm(t('admin.system.site.deleteConfirm'), t('admin.common.notice'), {type: 'warning'})
  await siteApi.remove(row.id)
  ElMessage.success(t('admin.common.delete'))
  await load()
}
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <!-- 搜索区 -->
      <el-form :inline="true" :model="query" @submit.prevent="search()">
        <el-form-item :label="$t('admin.system.sensitiveWord.keyword')">
          <el-input
            v-model="query.keyword"
            :placeholder="$t('admin.system.site.keywordPlaceholder')"
            clearable
            style="width: 200px"
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
          <el-button type="primary" @click="search()">{{ $t('admin.common.search') }}</el-button>
          <el-button @click="reset()">{{ $t('admin.common.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <!-- 操作区 -->
      <div class="table-toolbar">
        <el-button v-auth="'module_system:site:create'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.system.site.createTitle') }}
        </el-button>
        <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: total}) }}</span>
      </div>

      <!-- 表格 -->
      <AdminTableSkeleton v-if="loading && !list.length" :rows="5"/>

      <AdminEmpty v-else-if="!loading && !list.length" :title="$t('admin.common.empty')"/>
      <el-table v-else v-loading="loading" :data="list" border stripe>
        <el-table-column :label="$t('admin.common.name')" min-width="140" prop="name" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.site.slug')" prop="slug" width="120"/>
        <el-table-column :label="$t('admin.system.site.domain')" min-width="160" prop="domain" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.site.additionalDomains')" min-width="160">
          <template #default="{ row }">
            {{ ((row as SiteItem).additional_domains || []).join(', ') || '—' }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.site.theme')" prop="theme" width="110"/>
        <el-table-column :label="$t('admin.system.site.isDefault')" width="90">
          <template #default="{ row }">
            <el-tag v-if="(row as SiteItem).is_default" size="small" type="warning">
              {{ $t('admin.system.site.defaultTag') }}
            </el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.status')" width="90">
          <template #default="{ row }">
            <el-tag :type="(row as SiteItem).is_active ? 'success' : 'info'" size="small">
              {{
                (row as SiteItem).is_active ? $t('admin.system.sensitiveWord.active') : $t('admin.system.sensitiveWord.inactive')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
          <template #default="{ row }">
            <el-button v-auth="'module_system:site:edit'" link type="primary"
                       @click="openEdit(row as SiteItem)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button v-auth="'module_system:site:delete'" link type="danger"
                       @click="onDelete(row as SiteItem)">
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
    <el-drawer v-model="formVisible" :title="formTitle" destroy-on-close size="520px">
      <el-form :model="form" label-width="110px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="form.name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.slug')" :required="!editingId">
          <el-input v-model="form.slug" :disabled="!!editingId"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.domain')" required>
          <el-input v-model="form.domain" placeholder="blog.example.com"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.additionalDomains')">
          <el-input v-model="form.additional_domains" :placeholder="$t('admin.system.site.additionalDomainsHint')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.theme')">
          <el-input v-model="form.theme"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.language')">
          <el-input v-model="form.language" placeholder="zh-CN"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.timezone')">
          <el-input v-model="form.timezone" placeholder="Asia/Shanghai"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.isDefault')">
          <el-switch v-model="form.is_default"/>
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
