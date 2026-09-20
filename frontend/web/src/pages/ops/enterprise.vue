<script lang="ts" setup>
/**
 * 企业版授权（T5-11 批次 6）
 *
 * 对齐 v3 `/ops/enterprise`：企业许可证 + 数据保留策略（双标签）。
 * 页面骨架与 system/sensitive-words 一致：搜索区 + 表格 + 抽屉表单。
 * `features` 走后端 JSON 字符串列，这里用「每行一项」的多行文本与之互转；
 * `max_sites = -1` 表示不限站点数。
 */
import {Delete, EditPen, Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {type DataRetentionPolicyItem, enterpriseApi, type EnterpriseLicenseItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useTable} from '@/hooks/useTable'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ops.enterprise.title',
  permission: 'module_ops:enterprise:view',
})

const {t} = useI18n()
const activeTab = ref('license')

// ---------------------------------------------------------------- 企业许可证
interface LicenseQueryForm extends PageQuery {
  keyword?: string
}

const {
  list: licenseList,
  loading: licenseLoading,
  total: licenseTotal,
  page: licensePage,
  pageSize: licensePageSize,
  query: licenseQuery,
  search: licenseSearch,
  reset: licenseReset,
  load: licenseLoad,
  onPageChange: onLicensePageChange,
  onSizeChange: onLicenseSizeChange,
} = useTable<EnterpriseLicenseItem, LicenseQueryForm>({
  fetcher: (params) => enterpriseApi.listLicenses(params),
  defaultQuery: {keyword: ''},
})

const licenseFormVisible = ref(false)
const licenseEditingId = ref<number | null>(null)
const licenseSaving = ref(false)
const licenseForm = reactive({
  license_key: '',
  license_type: 'professional',
  company_name: '',
  contact_email: '',
  max_sites: -1,
  features_text: '',
  valid_from: '',
  valid_until: '',
  support_level: 'standard',
  sla_enabled: false,
  sla_uptime_guarantee: undefined as number | undefined,
  is_active: true,
})

const licenseFormTitle = computed(() =>
  licenseEditingId.value
    ? t('admin.ops.enterprise.editLicense')
    : t('admin.ops.enterprise.createLicense'),
)

function resetLicenseForm() {
  Object.assign(licenseForm, {
    license_key: '',
    license_type: 'professional',
    company_name: '',
    contact_email: '',
    max_sites: -1,
    features_text: '',
    valid_from: '',
    valid_until: '',
    support_level: 'standard',
    sla_enabled: false,
    sla_uptime_guarantee: undefined,
    is_active: true,
  })
}

function openLicenseCreate() {
  licenseEditingId.value = null
  resetLicenseForm()
  licenseFormVisible.value = true
}

function openLicenseEdit(row: EnterpriseLicenseItem) {
  licenseEditingId.value = row.id
  Object.assign(licenseForm, {
    license_key: row.license_key || '',
    license_type: row.license_type || 'professional',
    company_name: row.company_name || '',
    contact_email: row.contact_email || '',
    max_sites: row.max_sites ?? -1,
    features_text: (row.features ?? []).join('\n'),
    valid_from: (row.valid_from || '').slice(0, 19).replace('T', ' '),
    valid_until: (row.valid_until || '').slice(0, 19).replace('T', ' '),
    support_level: row.support_level || 'standard',
    sla_enabled: row.sla_enabled,
    sla_uptime_guarantee: row.sla_uptime_guarantee ?? undefined,
    is_active: row.is_active,
  })
  licenseFormVisible.value = true
}

/** 多行文本 → 功能列表；全空则 null（后端可选字段，null 即不下发） */
function parseFeatures(text: string): string[] | null {
  const items = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
  return items.length ? items : null
}

async function submitLicense() {
  if (!licenseEditingId.value && !licenseForm.license_key.trim()) {
    ElMessage.warning(t('admin.ops.enterprise.licenseKeyRequired'))
    return
  }
  licenseSaving.value = true
  try {
    const payload = {
      license_key: licenseForm.license_key.trim(),
      license_type: licenseForm.license_type || 'professional',
      company_name: licenseForm.company_name || null,
      contact_email: licenseForm.contact_email || null,
      max_sites: licenseForm.max_sites,
      features: parseFeatures(licenseForm.features_text),
      valid_from: licenseForm.valid_from || null,
      valid_until: licenseForm.valid_until || null,
      support_level: licenseForm.support_level || 'standard',
      sla_enabled: licenseForm.sla_enabled,
      sla_uptime_guarantee: licenseForm.sla_uptime_guarantee ?? null,
      is_active: licenseForm.is_active,
    }
    if (licenseEditingId.value) {
      await enterpriseApi.updateLicense(licenseEditingId.value, payload)
    } else {
      await enterpriseApi.createLicense(payload)
    }
    ElMessage.success(t('admin.common.save'))
    licenseFormVisible.value = false
    await licenseLoad()
  } finally {
    licenseSaving.value = false
  }
}

async function onDeleteLicense(row: EnterpriseLicenseItem) {
  await ElMessageBox.confirm(
    t('admin.ops.enterprise.deleteLicenseConfirm', {
      name: row.license_key || row.company_name || row.id,
    }),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await enterpriseApi.removeLicense(row.id)
  ElMessage.success(t('admin.common.delete'))
  await licenseLoad()
}

// ---------------------------------------------------------------- 数据保留策略
interface PolicyQueryForm extends PageQuery {
  keyword?: string
}

const {
  list: policyList,
  loading: policyLoading,
  total: policyTotal,
  page: policyPage,
  pageSize: policyPageSize,
  query: policyQuery,
  search: policySearch,
  reset: policyReset,
  load: policyLoad,
  onPageChange: onPolicyPageChange,
  onSizeChange: onPolicySizeChange,
} = useTable<DataRetentionPolicyItem, PolicyQueryForm>({
  fetcher: (params) => enterpriseApi.listPolicies(params),
  defaultQuery: {keyword: ''},
})

const policyFormVisible = ref(false)
const policyEditingId = ref<number | null>(null)
const policySaving = ref(false)
const policyForm = reactive({
  data_category: '',
  retention_days: 90,
  action: 'delete',
  is_active: true,
})

const policyFormTitle = computed(() =>
  policyEditingId.value
    ? t('admin.ops.enterprise.editPolicy')
    : t('admin.ops.enterprise.createPolicy'),
)

function openPolicyCreate() {
  policyEditingId.value = null
  Object.assign(policyForm, {data_category: '', retention_days: 90, action: 'delete', is_active: true})
  policyFormVisible.value = true
}

function openPolicyEdit(row: DataRetentionPolicyItem) {
  policyEditingId.value = row.id
  Object.assign(policyForm, {
    data_category: row.data_category,
    retention_days: row.retention_days,
    action: row.action || 'delete',
    is_active: row.is_active,
  })
  policyFormVisible.value = true
}

async function submitPolicy() {
  if (!policyForm.data_category.trim()) {
    ElMessage.warning(t('admin.ops.enterprise.dataCategoryRequired'))
    return
  }
  if (!policyForm.retention_days || policyForm.retention_days < 1) {
    ElMessage.warning(t('admin.ops.enterprise.retentionDaysRequired'))
    return
  }
  policySaving.value = true
  try {
    const payload = {
      data_category: policyForm.data_category.trim(),
      retention_days: policyForm.retention_days,
      action: policyForm.action,
      is_active: policyForm.is_active,
    }
    if (policyEditingId.value) {
      await enterpriseApi.updatePolicy(policyEditingId.value, payload)
    } else {
      await enterpriseApi.createPolicy(payload)
    }
    ElMessage.success(t('admin.common.save'))
    policyFormVisible.value = false
    await policyLoad()
  } finally {
    policySaving.value = false
  }
}

async function onDeletePolicy(row: DataRetentionPolicyItem) {
  await ElMessageBox.confirm(
    t('admin.ops.enterprise.deletePolicyConfirm', {name: row.data_category}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await enterpriseApi.removePolicy(row.id)
  ElMessage.success(t('admin.common.delete'))
  await policyLoad()
}
</script>

<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- 企业许可证 -->
      <el-tab-pane :label="$t('admin.ops.enterprise.licenses')" name="license">
        <el-card shadow="never">
          <el-form :inline="true" :model="licenseQuery" @submit.prevent="licenseSearch()">
            <el-form-item :label="$t('admin.common.search')">
              <el-input
                v-model="licenseQuery.keyword"
                :placeholder="$t('admin.ops.enterprise.keywordPlaceholder')"
                clearable
                style="width: 220px"
                @keyup.enter="licenseSearch()"
              />
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="licenseSearch()">
                {{ $t('admin.common.search') }}
              </el-button>
              <el-button :icon="Refresh" @click="licenseReset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>

          <div class="table-toolbar">
            <el-button
              v-auth="'module_ops:enterprise:edit'"
              :icon="Plus"
              type="primary"
              @click="openLicenseCreate"
            >
              {{ $t('admin.ops.enterprise.createLicense') }}
            </el-button>
            <span class="table-toolbar__total">
              {{ $t('admin.common.totalItems', {n: licenseTotal}) }}
            </span>
          </div>

          <el-table v-loading="licenseLoading" :data="licenseList" border stripe>
            <el-table-column
              :label="$t('admin.ops.enterprise.licenseKey')"
              min-width="200"
              prop="license_key"
              show-overflow-tooltip
            />
            <el-table-column :label="$t('admin.ops.enterprise.licenseType')" prop="license_type" width="130"/>
            <el-table-column
              :label="$t('admin.ops.enterprise.companyName')"
              min-width="160"
              prop="company_name"
              show-overflow-tooltip
            />
            <el-table-column :label="$t('admin.ops.enterprise.maxSites')" align="center" width="110">
              <template #default="{ row }">
                <span v-if="(row as EnterpriseLicenseItem).max_sites === -1">∞</span>
                <span v-else>{{ (row as EnterpriseLicenseItem).max_sites }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.ops.enterprise.validUntil')" width="170">
              <template #default="{ row }">
                {{ (row as EnterpriseLicenseItem).valid_until || '-' }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.ops.enterprise.slaEnabled')" align="center" width="100">
              <template #default="{ row }">
                <el-tag :type="(row as EnterpriseLicenseItem).sla_enabled ? 'success' : 'info'" size="small">
                  {{ (row as EnterpriseLicenseItem).sla_enabled ? $t('admin.common.yes') : $t('admin.common.no') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.status')" align="center" width="100">
              <template #default="{ row }">
                <el-tag :type="(row as EnterpriseLicenseItem).is_active ? 'success' : 'info'" size="small">
                  {{
                    (row as EnterpriseLicenseItem).is_active ? $t('admin.common.enabled') : $t('admin.common.disabled')
                  }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
              <template #default="{ row }">
                <el-button
                  v-auth="'module_ops:enterprise:edit'"
                  :icon="EditPen"
                  link
                  type="primary"
                  @click="openLicenseEdit(row as EnterpriseLicenseItem)"
                >
                  {{ $t('admin.common.edit') }}
                </el-button>
                <el-button
                  v-auth="'module_ops:enterprise:edit'"
                  :icon="Delete"
                  link
                  type="danger"
                  @click="onDeleteLicense(row as EnterpriseLicenseItem)"
                >
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            :current-page="licensePage"
            :page-size="licensePageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="licenseTotal"
            background
            class="table-pagination"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="onLicensePageChange"
            @size-change="onLicenseSizeChange"
          />
        </el-card>
      </el-tab-pane>

      <!-- 数据保留策略 -->
      <el-tab-pane :label="$t('admin.ops.enterprise.retention')" name="retention">
        <el-card shadow="never">
          <el-form :inline="true" :model="policyQuery" @submit.prevent="policySearch()">
            <el-form-item :label="$t('admin.common.search')">
              <el-input
                v-model="policyQuery.keyword"
                :placeholder="$t('admin.ops.enterprise.dataCategoryPlaceholder')"
                clearable
                style="width: 220px"
                @keyup.enter="policySearch()"
              />
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="policySearch()">
                {{ $t('admin.common.search') }}
              </el-button>
              <el-button :icon="Refresh" @click="policyReset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>

          <div class="table-toolbar">
            <el-button
              v-auth="'module_ops:enterprise:edit'"
              :icon="Plus"
              type="primary"
              @click="openPolicyCreate"
            >
              {{ $t('admin.ops.enterprise.createPolicy') }}
            </el-button>
            <span class="table-toolbar__total">
              {{ $t('admin.common.totalItems', {n: policyTotal}) }}
            </span>
          </div>

          <el-table v-loading="policyLoading" :data="policyList" border stripe>
            <el-table-column
              :label="$t('admin.ops.enterprise.dataCategory')"
              min-width="180"
              prop="data_category"
              show-overflow-tooltip
            />
            <el-table-column :label="$t('admin.ops.enterprise.retentionDays')" align="center" prop="retention_days"
                             width="120"/>
            <el-table-column :label="$t('admin.ops.enterprise.action')" width="120">
              <template #default="{ row }">
                {{
                  (row as DataRetentionPolicyItem).action === 'archive'
                    ? $t('admin.ops.enterprise.actionArchive')
                    : $t('admin.ops.enterprise.actionDelete')
                }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.status')" align="center" width="100">
              <template #default="{ row }">
                <el-tag :type="(row as DataRetentionPolicyItem).is_active ? 'success' : 'info'" size="small">
                  {{
                    (row as DataRetentionPolicyItem).is_active ? $t('admin.common.enabled') : $t('admin.common.disabled')
                  }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
              <template #default="{ row }">
                <el-button
                  v-auth="'module_ops:enterprise:edit'"
                  :icon="EditPen"
                  link
                  type="primary"
                  @click="openPolicyEdit(row as DataRetentionPolicyItem)"
                >
                  {{ $t('admin.common.edit') }}
                </el-button>
                <el-button
                  v-auth="'module_ops:enterprise:edit'"
                  :icon="Delete"
                  link
                  type="danger"
                  @click="onDeletePolicy(row as DataRetentionPolicyItem)"
                >
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            :current-page="policyPage"
            :page-size="policyPageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="policyTotal"
            background
            class="table-pagination"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="onPolicyPageChange"
            @size-change="onPolicySizeChange"
          />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 许可证：新建 / 编辑 -->
    <el-drawer v-model="licenseFormVisible" :title="licenseFormTitle" destroy-on-close size="520px">
      <el-form :model="licenseForm" label-width="130px">
        <el-form-item :label="$t('admin.ops.enterprise.licenseKey')" required>
          <el-input
            v-model="licenseForm.license_key"
            :placeholder="$t('admin.ops.enterprise.licenseKeyPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.ops.enterprise.licenseType')">
          <el-select v-model="licenseForm.license_type" style="width: 100%">
            <el-option label="professional" value="professional"/>
            <el-option label="enterprise" value="enterprise"/>
            <el-option label="trial" value="trial"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.enterprise.companyName')">
          <el-input v-model="licenseForm.company_name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.enterprise.contactEmail')">
          <el-input v-model="licenseForm.contact_email"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.enterprise.maxSites')">
          <el-input-number v-model="licenseForm.max_sites" :min="-1" style="width: 100%"/>
          <div class="form-hint">{{ $t('admin.ops.enterprise.maxSitesHint') }}</div>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.enterprise.features')">
          <el-input
            v-model="licenseForm.features_text"
            :autosize="{minRows: 3, maxRows: 8}"
            :placeholder="$t('admin.ops.enterprise.featuresPlaceholder')"
            type="textarea"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.ops.enterprise.validFrom')">
          <el-date-picker
            v-model="licenseForm.valid_from"
            style="width: 100%"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.ops.enterprise.validUntil')">
          <el-date-picker
            v-model="licenseForm.valid_until"
            style="width: 100%"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.ops.enterprise.supportLevel')">
          <el-select v-model="licenseForm.support_level" style="width: 100%">
            <el-option label="standard" value="standard"/>
            <el-option label="premium" value="premium"/>
            <el-option label="dedicated" value="dedicated"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.enterprise.slaEnabled')">
          <el-switch v-model="licenseForm.sla_enabled"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.enterprise.slaUptime')">
          <el-input-number
            v-model="licenseForm.sla_uptime_guarantee"
            :max="100"
            :min="0"
            :precision="2"
            :step="0.1"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="licenseForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="licenseFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="licenseSaving" type="primary" @click="submitLicense">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-drawer>

    <!-- 保留策略：新建 / 编辑 -->
    <el-drawer v-model="policyFormVisible" :title="policyFormTitle" destroy-on-close size="480px">
      <el-form :model="policyForm" label-width="110px">
        <el-form-item :label="$t('admin.ops.enterprise.dataCategory')" required>
          <el-input
            v-model="policyForm.data_category"
            :placeholder="$t('admin.ops.enterprise.dataCategoryPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.ops.enterprise.retentionDays')" required>
          <el-input-number v-model="policyForm.retention_days" :min="1" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.enterprise.action')">
          <el-select v-model="policyForm.action" style="width: 100%">
            <el-option :label="$t('admin.ops.enterprise.actionDelete')" value="delete"/>
            <el-option :label="$t('admin.ops.enterprise.actionArchive')" value="archive"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="policyForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="policyFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="policySaving" type="primary" @click="submitPolicy">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.form-hint {
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-secondary);
}
</style>
