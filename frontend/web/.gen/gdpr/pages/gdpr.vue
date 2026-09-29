<script lang="ts" setup>
/**
 * GDPR 合规同意记录（T5-11 批次 3）
 *
 * 对齐 v3 `/system/gdpr`：同意记录列表 / 统计 / 删除。
 * 同意记录由前台授权动作写入，本页只读 + 治理（删除过期记录）。
 */
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {onMounted, ref} from 'vue'

import type {GdprCheckItem, GdprComplianceReport, GdprCookieConsent, GdprPrivacyPolicy} from '@/api'
import {gdprApi, type GdprConsentItem, type GdprStats} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.gdpr.title',
  permission: 'module_system:gdpr:view',
})

const {t} = useI18n()

interface GdprQueryForm extends PageQuery {
  user_id?: number
  consent_type?: string
  granted?: boolean
}

const list = useAdminList<GdprConsentItem, GdprQueryForm>({
  fetcher: (params) => gdprApi.list(params),
  defaultQuery: {consent_type: '', granted: undefined},
  syncUrl: true,
})

const stats = ref<GdprStats | null>(null)

async function loadStats(): Promise<void> {
  try {
    stats.value = await gdprApi.stats()
  } catch {
    stats.value = null
  }
}

onMounted(loadStats)

async function onDelete(row: GdprConsentItem) {
  await ElMessageBox.confirm(t('admin.system.gdpr.deleteConfirm'), t('admin.common.notice'), {type: 'warning'})
  await gdprApi.remove(row.id)
  ElMessage.success(t('admin.common.delete'))
  await loadStats()
  await list.reload()
}

// ─────────────────────── 追加：合规检查与合规文档 ───────────────────────

/** 合规区块内当前选中的标签页 */
const activeTab = ref('check')

const compliance = ref<GdprComplianceReport | null>(null)
const complianceLoading = ref(false)
const complianceFailed = ref(false)

/** 拉取 GDPR / PCI DSS 合规检查结果 */
async function loadCompliance(): Promise<void> {
  complianceLoading.value = true
  complianceFailed.value = false
  try {
    compliance.value = await gdprApi.checkCompliance()
  } catch {
    // 失败提示由 request 层统一弹出
    complianceFailed.value = true
  } finally {
    complianceLoading.value = false
  }
}

const cookieConsent = ref<GdprCookieConsent | null>(null)
const cookieLoading = ref(false)

/** 生成 Cookie 同意横幅 HTML */
async function loadCookieConsent(): Promise<void> {
  cookieLoading.value = true
  try {
    cookieConsent.value = await gdprApi.cookieConsent()
  } finally {
    cookieLoading.value = false
  }
}

const privacyPolicy = ref<GdprPrivacyPolicy | null>(null)
const privacyLoading = ref(false)

/** 生成隐私政策（asHtml 为 false 时返回 Markdown） */
async function loadPrivacyPolicy(asHtml = false): Promise<void> {
  privacyLoading.value = true
  try {
    privacyPolicy.value = await gdprApi.privacyPolicy(asHtml)
  } finally {
    privacyLoading.value = false
  }
}

/** 检查状态的展示文案 key（避免在模板里拼接 key） */
const statusLabelKey: Record<GdprCheckItem['status'], string> = {
  ok: 'admin.system.gdpr.statusOk',
  warn: 'admin.system.gdpr.statusWarn',
  fail: 'admin.system.gdpr.statusFail',
}

/** 检查状态 -> el-tag 的 type */
function checkTagType(status: GdprCheckItem['status']): 'success' | 'warning' | 'danger' {
  if (status === 'ok') return 'success'
  if (status === 'warn') return 'warning'
  return 'danger'
}

/** 切换标签页时按需懒加载（首次进入才请求） */
function onTabChange(name: string | number): void {
  if (name === 'check' && !compliance.value) {
    void loadCompliance()
  } else if (name === 'cookie' && !cookieConsent.value) {
    void loadCookieConsent()
  } else if (name === 'privacy' && !privacyPolicy.value) {
    void loadPrivacyPolicy()
  }
}

/** 复制文档生成结果到剪贴板 */
async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(t('admin.system.gdpr.copied'))
  } catch {
    ElMessage.warning(t('admin.system.gdpr.copyFailed'))
  }
}
</script>

<template>
  <AdminPage :desc="$t('admin.system.gdpr.desc')" :title="$t('admin.system.gdpr.title')">
    <!-- 统计卡：属于页面级信息，放在列表壳之外 -->
    <div v-if="stats" class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
      <el-card shadow="never">
        <div class="text-xs text-fg-subtle">{{ $t('admin.system.gdpr.statTotal') }}</div>
        <div class="mt-1 text-xl font-semibold text-fg">{{ stats.total }}</div>
      </el-card>
      <el-card shadow="never">
        <div class="text-xs text-fg-subtle">{{ $t('admin.system.gdpr.statGranted') }}</div>
        <div class="mt-1 text-xl font-semibold text-fg">{{ stats.granted }}</div>
      </el-card>
      <el-card shadow="never">
        <div class="text-xs text-fg-subtle">{{ $t('admin.system.gdpr.statRevoked') }}</div>
        <div class="mt-1 text-xl font-semibold text-fg">{{ stats.revoked }}</div>
      </el-card>
      <el-card shadow="never">
        <div class="text-xs text-fg-subtle">{{ $t('admin.system.gdpr.statTypes') }}</div>
        <div class="mt-1 text-xl font-semibold text-fg">{{ Object.keys(stats.by_type || {}).length }}</div>
      </el-card>
    </div>

    <AdminListShell
      :empty-desc="list.hasFilters.value ? $t('admin.system.gdpr.emptyFiltered') : $t('admin.system.gdpr.emptyDesc')"
      :empty-title="$t('admin.system.gdpr.emptyTitle')"
      :failed="list.failed.value"
      :loading="list.loading.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      :rows="list.rows.value"
      :selectable="false"
      :total="list.total.value"
      @refresh="list.reload"
      @reset="list.reset"
      @search="list.search"
      @page-change="list.onPageChange"
      @size-change="list.onSizeChange"
    >
      <template #filters>
        <el-form-item :label="$t('admin.system.gdpr.consentType')">
          <el-input
            v-model="list.query.consent_type"
            :placeholder="$t('admin.system.gdpr.consentTypePlaceholder')"
            clearable
            style="width: 180px"
            @keyup.enter="list.search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.system.gdpr.granted')">
          <el-select v-model="list.query.granted" :placeholder="$t('admin.common.all')" clearable style="width: 110px">
            <el-option :label="$t('admin.system.gdpr.grantedYes')" :value="true"/>
            <el-option :label="$t('admin.system.gdpr.grantedNo')" :value="false"/>
          </el-select>
        </el-form-item>
      </template>

      <el-table-column label="ID" prop="id" width="80"/>
      <el-table-column :label="$t('admin.system.gdpr.userId')" prop="user_id" width="100"/>
      <el-table-column :label="$t('admin.system.gdpr.consentType')" min-width="140" prop="consent_type"
                       show-overflow-tooltip/>
      <el-table-column :label="$t('admin.system.gdpr.granted')" width="100">
        <template #default="{ row }">
          <el-tag :type="(row as GdprConsentItem).granted ? 'success' : 'info'" size="small">
            {{
              (row as GdprConsentItem).granted ? $t('admin.system.gdpr.grantedYes') : $t('admin.system.gdpr.grantedNo')
            }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.system.gdpr.details')" min-width="160" prop="details"
                       show-overflow-tooltip/>
      <el-table-column :label="$t('admin.system.gdpr.ipAddress')" min-width="130" prop="ip_address"
                       show-overflow-tooltip/>
      <el-table-column :label="$t('admin.common.createdAt')" min-width="170" prop="created_at" show-overflow-tooltip/>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="100">
        <template #default="{ row }">
          <el-button
            v-auth="'module_system:gdpr:delete'"
            link
            type="danger"
            @click="onDelete(row as GdprConsentItem)"
          >
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>

    <!-- ── 追加：合规检查 / Cookie 同意 / 隐私政策 ── -->
    <el-divider content-position="left">{{ $t('admin.system.gdpr.complianceSection') }}</el-divider>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- 合规检查 -->
      <el-tab-pane :label="$t('admin.system.gdpr.tabCheck')" name="check">
        <div class="mb-3 flex items-center gap-3">
          <el-button
            v-auth="'module_system:gdpr:view'"
            :loading="complianceLoading"
            type="primary"
            @click="loadCompliance"
          >
            {{ $t('admin.system.gdpr.runCheck') }}
          </el-button>
          <span v-if="compliance" class="text-xs text-fg-subtle">
            {{ $t('admin.system.gdpr.generatedAt') }}: {{ compliance.generated_at }}
          </span>
        </div>

        <el-alert
          v-if="complianceFailed"
          :closable="false"
          :title="$t('admin.common.loadFailed')"
          class="mb-3"
          show-icon
          type="error"
        />

        <template v-if="compliance">
          <!-- 当前合规配置回显 -->
          <el-descriptions
            :column="3"
            :title="$t('admin.system.gdpr.settingsTitle')"
            border
            class="mb-4"
            size="small"
          >
            <el-descriptions-item :label="$t('admin.system.gdpr.settingRetention')">
              {{ compliance.settings.retention_days }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.gdpr.settingRequireConsent')">
              {{ compliance.settings.require_consent ? $t('admin.common.yes') : $t('admin.common.no') }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.gdpr.settingAllowExport')">
              {{ compliance.settings.allow_data_export ? $t('admin.common.yes') : $t('admin.common.no') }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.gdpr.settingAllowDeletion')">
              {{ compliance.settings.allow_data_deletion ? $t('admin.common.yes') : $t('admin.common.no') }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.gdpr.settingContactEmail')">
              {{ compliance.settings.contact_email || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.gdpr.settingPrivacyUrl')">
              {{ compliance.settings.privacy_policy_url || '-' }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- GDPR 检查项 -->
          <div class="mb-1 flex items-center gap-2 font-medium">
            <span>{{ $t('admin.system.gdpr.groupGdpr') }}</span>
            <el-tag size="small" type="success">ok {{ compliance.gdpr.summary.ok }}</el-tag>
            <el-tag size="small" type="warning">warn {{ compliance.gdpr.summary.warn }}</el-tag>
            <el-tag size="small" type="danger">fail {{ compliance.gdpr.summary.fail }}</el-tag>
          </div>
          <el-table :data="compliance.gdpr.items" border class="mb-4" size="small">
            <el-table-column :label="$t('admin.system.gdpr.checkItem')" min-width="160" prop="key"/>
            <el-table-column :label="$t('admin.system.gdpr.checkStatus')" width="100">
              <template #default="{ row }">
                <el-tag :type="checkTagType((row as GdprCheckItem).status)" size="small">
                  {{ $t(statusLabelKey[(row as GdprCheckItem).status]) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              :label="$t('admin.system.gdpr.checkMessage')"
              min-width="260"
              prop="message"
              show-overflow-tooltip
            />
          </el-table>

          <!-- PCI DSS 检查项 -->
          <div class="mb-1 flex items-center gap-2 font-medium">
            <span>{{ $t('admin.system.gdpr.groupPci') }}</span>
            <el-tag size="small" type="success">ok {{ compliance.pci_dss.summary.ok }}</el-tag>
            <el-tag size="small" type="warning">warn {{ compliance.pci_dss.summary.warn }}</el-tag>
            <el-tag size="small" type="danger">fail {{ compliance.pci_dss.summary.fail }}</el-tag>
          </div>
          <el-table :data="compliance.pci_dss.items" border size="small">
            <el-table-column :label="$t('admin.system.gdpr.checkItem')" min-width="160" prop="key"/>
            <el-table-column :label="$t('admin.system.gdpr.checkStatus')" width="100">
              <template #default="{ row }">
                <el-tag :type="checkTagType((row as GdprCheckItem).status)" size="small">
                  {{ $t(statusLabelKey[(row as GdprCheckItem).status]) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              :label="$t('admin.system.gdpr.checkMessage')"
              min-width="260"
              prop="message"
              show-overflow-tooltip
            />
          </el-table>
        </template>
      </el-tab-pane>

      <!-- Cookie 同意横幅 -->
      <el-tab-pane :label="$t('admin.system.gdpr.tabCookie')" name="cookie">
        <p class="mb-2 text-xs text-fg-subtle">{{ $t('admin.system.gdpr.cookieHint') }}</p>
        <div class="mb-3 flex gap-3">
          <el-button
            v-auth="'module_system:gdpr:view'"
            :loading="cookieLoading"
            type="primary"
            @click="loadCookieConsent"
          >
            {{ $t('admin.system.gdpr.generateCookie') }}
          </el-button>
          <el-button v-if="cookieConsent" @click="copyText(cookieConsent.content)">
            {{ $t('admin.system.gdpr.copy') }}
          </el-button>
        </div>
        <el-input
          v-if="cookieConsent"
          :model-value="cookieConsent.content"
          :rows="12"
          readonly
          type="textarea"
        />
      </el-tab-pane>

      <!-- 隐私政策 -->
      <el-tab-pane :label="$t('admin.system.gdpr.tabPrivacy')" name="privacy">
        <p class="mb-2 text-xs text-fg-subtle">{{ $t('admin.system.gdpr.privacyHint') }}</p>
        <div class="mb-3 flex gap-3">
          <el-button
            v-auth="'module_system:gdpr:view'"
            :loading="privacyLoading"
            type="primary"
            @click="loadPrivacyPolicy(false)"
          >
            {{ $t('admin.system.gdpr.generatePrivacyMarkdown') }}
          </el-button>
          <el-button
            v-auth="'module_system:gdpr:view'"
            :loading="privacyLoading"
            @click="loadPrivacyPolicy(true)"
          >
            {{ $t('admin.system.gdpr.generatePrivacyHtml') }}
          </el-button>
          <el-button v-if="privacyPolicy" @click="copyText(privacyPolicy.content)">
            {{ $t('admin.system.gdpr.copy') }}
          </el-button>
        </div>
        <el-input
          v-if="privacyPolicy"
          :model-value="privacyPolicy.content"
          :rows="16"
          readonly
          type="textarea"
        />
      </el-tab-pane>
    </el-tabs>
  </AdminPage>
</template>
