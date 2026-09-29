<script lang="ts" setup>
/**
 * 边缘函数控制台（/system/edge，system 域）
 *
 * 对齐后端 `src/api/v3/modules/system/edge`（Cloudflare Workers / Vercel Edge）的 7 个端点：
 * 函数列表 / 注册 / 详情 / 删除 / 静态校验 / 部署 / 本地日志。
 *
 * 关键语义（**如实呈现，不美化**）：
 *  - 后端**从不执行**用户提交的代码，校验 / 部署只做静态检查并生成产物摘要；
 *  - `deploy` 在缺少平台凭据时返回 `deployed=false` + `reason` + 所需环境变量清单，
 *    页面把这个原因**原样**展示，绝不显示成「成功」；
 *  - 后端**没有更新端点**：已注册函数的改动无法保存，只能删除后重新注册（UI 已明确提示）。
 *
 * 权限码取自 `controller.py` 的 `AuthControl(...)`（反查 `core/permission/codes.py`）：
 * view / create / edit / delete。
 */
import {Delete, Plus, Refresh, Upload, View} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {
  edgeApi,
  type EdgeDeployLogEntry,
  type EdgeDeployResult,
  type EdgeFunctionSummary,
  type EdgeLogResult,
  type EdgeValidationResult,
} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.edge.title',
  permission: 'module_system:integration:view',
})

const {t} = useI18n()

/** 平台下拉（value 为后端标准名，label 走 i18n） */
const PLATFORMS = [
  {value: 'cloudflare_workers', labelKey: 'admin.system.edge.platformCloudflare'},
  {value: 'vercel_edge', labelKey: 'admin.system.edge.platformVercel'},
] as const

function platformLabel(platform: string): string {
  const item = PLATFORMS.find((p) => p.value === platform)
  return item ? t(item.labelKey) : platform
}

function severityType(severity: string): 'danger' | 'warning' | 'info' {
  if (severity === 'error') return 'danger'
  if (severity === 'warning') return 'warning'
  return 'info'
}

// ---------------------------------------------------------------- 列表
const loading = ref(false)
const failed = ref(false)
const rows = ref<EdgeFunctionSummary[]>([])
const total = ref(0)

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  // 只读加载：用 allSettled，单项失败不拖垮整页
  const [list] = await Promise.allSettled([edgeApi.listFunctions()])
  if (list.status === 'fulfilled') {
    rows.value = list.value.items
    total.value = list.value.total
  } else {
    rows.value = []
    total.value = 0
    failed.value = true
  }
  loading.value = false
}

// ---------------------------------------------------------------- 编辑器抽屉
const drawerVisible = ref(false)
const saving = ref(false)
const loadingDetail = ref(false)
const validating = ref(false)
const editing = ref(false)
const editingName = ref<string | null>(null)
const validation = ref<EdgeValidationResult | null>(null)

const form = reactive({
  name: '',
  platform: 'cloudflare_workers' as string,
  route: '',
  code: '',
  cache_ttl: 0,
  description: '',
  enabled: true,
})

const drawerTitle = computed(() =>
  t(editing.value ? 'admin.system.edge.editTitle' : 'admin.system.edge.createTitle'),
)

function resetForm(): void {
  Object.assign(form, {
    name: '',
    platform: 'cloudflare_workers',
    route: '',
    code: '',
    cache_ttl: 0,
    description: '',
    enabled: true,
  })
  validation.value = null
}

function openCreate(): void {
  editing.value = false
  editingName.value = null
  resetForm()
  drawerVisible.value = true
}

async function openDetail(row: EdgeFunctionSummary): Promise<void> {
  editing.value = true
  editingName.value = row.name
  validation.value = null
  drawerVisible.value = true
  loadingDetail.value = true
  try {
    const detail = await edgeApi.getFunction(row.name)
    Object.assign(form, {
      name: detail.name,
      platform: detail.platform,
      route: detail.route,
      code: detail.code,
      cache_ttl: detail.cache_ttl,
      description: detail.description,
      enabled: detail.enabled,
    })
  } finally {
    loadingDetail.value = false
  }
}

async function onSave(): Promise<void> {
  if (!form.name.trim()) {
    ElMessage.warning(t('admin.system.edge.nameRequired'))
    return
  }
  if (!form.route.trim()) {
    ElMessage.warning(t('admin.system.edge.routeRequired'))
    return
  }
  saving.value = true
  try {
    const res = await edgeApi.createFunction({
      name: form.name.trim(),
      platform: form.platform,
      route: form.route.trim(),
      code: form.code,
      cache_ttl: form.cache_ttl,
      description: form.description,
      enabled: form.enabled,
    })
    ElMessage.success(t('admin.system.edge.createSuccess'))
    // 注册成功但静态校验有错：如实提示（后端允许注册非法代码）
    if (!res.validation.valid) {
      ElMessage.warning(
        t('admin.system.edge.registeredInvalid', {n: res.validation.summary.errors}),
      )
    }
    drawerVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onValidate(): Promise<void> {
  if (!editing.value || !editingName.value) {
    // 后端 validate 要求函数已存在，未保存的新函数无法校验
    ElMessage.warning(t('admin.system.edge.registerFirstHint'))
    return
  }
  validating.value = true
  try {
    const res = await edgeApi.validateFunction(editingName.value, form.code)
    validation.value = res.validation
  } finally {
    validating.value = false
  }
}

// ---------------------------------------------------------------- 删除
const deletingName = ref<string | null>(null)

async function onDelete(row: EdgeFunctionSummary): Promise<void> {
  try {
    await ElMessageBox.confirm(
      t('admin.system.edge.removeConfirm', {name: row.name}),
      t('admin.common.notice'),
      {type: 'warning'},
    )
  } catch {
    return
  }
  deletingName.value = row.name
  try {
    await edgeApi.deleteFunction(row.name)
    ElMessage.success(t('admin.system.edge.removed'))
    await load()
  } finally {
    deletingName.value = null
  }
}

// ---------------------------------------------------------------- 部署
const deployingName = ref<string | null>(null)
const deployVisible = ref(false)
const deployResult = ref<EdgeDeployResult | null>(null)

const requiredEnv = computed(() => deployResult.value?.credentials?.required_env ?? [])

async function onDeploy(row: EdgeFunctionSummary): Promise<void> {
  deployingName.value = row.name
  try {
    const res = await edgeApi.deployFunction(row.name)
    deployResult.value = res
    deployVisible.value = true
    // 只有 deployed === true 才提示成功；否则如实提示「未部署」
    if (res.deployed) {
      ElMessage.success(t('admin.system.edge.deploySuccess'))
    } else {
      ElMessage.warning(t('admin.system.edge.deployNotDeployed'))
    }
  } finally {
    deployingName.value = null
  }
}

// ---------------------------------------------------------------- 日志
const logVisible = ref(false)
const logLoading = ref(false)
const logName = ref('')
const logResult = ref<EdgeLogResult | null>(null)

async function openLog(row: EdgeFunctionSummary): Promise<void> {
  logName.value = row.name
  logResult.value = null
  logVisible.value = true
  logLoading.value = true
  try {
    logResult.value = await edgeApi.logFunction(row.name, 50)
  } finally {
    logLoading.value = false
  }
}

onMounted(load)
</script>

<template>
  <AdminPage :desc="$t('admin.system.edge.desc')" :title="$t('admin.system.edge.title')">
    <template #actions>
      <el-button
        v-auth="'module_system:integration:create'"
        :icon="Plus"
        type="primary"
        @click="openCreate"
      >
        {{ $t('admin.system.edge.createFunction') }}
      </el-button>
      <el-button :icon="Refresh" :loading="loading" @click="load">
        {{ $t('admin.common.refresh') }}
      </el-button>
    </template>

    <!-- 如实呈现后端语义 -->
    <el-alert
      :closable="false"
      :title="$t('admin.system.edge.securityNotice')"
      class="mb-3"
      show-icon
      type="info"
    />
    <el-alert
      :closable="false"
      :title="$t('admin.system.edge.deployNotice')"
      class="mb-3"
      show-icon
      type="warning"
    />

    <el-alert
      v-if="failed"
      :closable="false"
      :title="$t('admin.common.loadFailed')"
      class="mb-3"
      show-icon
      type="error"
    />

    <section class="mcard">
      <div class="mcard__head">
        <span class="mcard__title">{{ $t('admin.system.edge.listSection') }}</span>
        <span class="hint">{{ $t('admin.system.edge.totalItems', {n: total}) }}</span>
      </div>

      <el-table v-if="rows.length" v-loading="loading" :data="rows" border stripe>
        <el-table-column
          :label="$t('admin.system.edge.colName')"
          min-width="150"
          prop="name"
          show-overflow-tooltip
        />
        <el-table-column :label="$t('admin.system.edge.colPlatform')" width="160">
          <template #default="{ row }">
            {{ platformLabel((row as EdgeFunctionSummary).platform) }}
          </template>
        </el-table-column>
        <el-table-column
          :label="$t('admin.system.edge.colRoute')"
          min-width="180"
          prop="route"
          show-overflow-tooltip
        />
        <el-table-column
          :label="$t('admin.system.edge.colCacheTtl')"
          align="right"
          prop="cache_ttl"
          width="120"
        />
        <el-table-column
          :label="$t('admin.system.edge.colCodeBytes')"
          align="right"
          prop="code_bytes"
          width="110"
        />
        <el-table-column :label="$t('admin.system.edge.colEnabled')" align="center" width="90">
          <template #default="{ row }">
            <el-tag :type="(row as EdgeFunctionSummary).enabled ? 'success' : 'info'" size="small">
              {{ (row as EdgeFunctionSummary).enabled ? $t('admin.common.yes') : $t('admin.common.no') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          :label="$t('admin.system.edge.colUpdatedAt')"
          min-width="170"
          prop="updated_at"
        />
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="320">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row as EdgeFunctionSummary)">
              {{ $t('admin.system.edge.viewEdit') }}
            </el-button>
            <el-button
              v-auth="'module_system:integration:edit'"
              :icon="Upload"
              :loading="deployingName === (row as EdgeFunctionSummary).name"
              link
              type="primary"
              @click="onDeploy(row as EdgeFunctionSummary)"
            >
              {{ $t('admin.system.edge.deploy') }}
            </el-button>
            <el-button :icon="View" link type="info" @click="openLog(row as EdgeFunctionSummary)">
              {{ $t('admin.system.edge.log') }}
            </el-button>
            <el-button
              v-auth="'module_system:integration:delete'"
              :icon="Delete"
              :loading="deletingName === (row as EdgeFunctionSummary).name"
              link
              type="danger"
              @click="onDelete(row as EdgeFunctionSummary)"
            >
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else :description="$t('admin.system.edge.empty')" :image-size="60"/>
    </section>

    <!-- 新建 / 详情（+ 静态校验） -->
    <el-drawer v-model="drawerVisible" :title="drawerTitle" destroy-on-close size="760px">
      <el-alert
        :closable="false"
        :title="$t('admin.system.edge.staticOnlyNotice')"
        class="mb-3"
        show-icon
        type="info"
      />
      <el-alert
        v-if="editing"
        :closable="false"
        :title="$t('admin.system.edge.noUpdateHint')"
        class="mb-3"
        show-icon
        type="warning"
      />
      <el-alert
        v-else
        :closable="false"
        :title="$t('admin.system.edge.registerFirstHint')"
        class="mb-3"
        show-icon
        type="info"
      />

      <el-form v-loading="loadingDetail" :model="form" label-width="130px">
        <el-form-item :label="$t('admin.system.edge.fieldName')" required>
          <el-input
            v-model="form.name"
            :disabled="editing"
            :placeholder="$t('admin.system.edge.namePlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.system.edge.fieldPlatform')" required>
          <el-select v-model="form.platform" style="width: 100%">
            <el-option
              v-for="item in PLATFORMS"
              :key="item.value"
              :label="$t(item.labelKey)"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.system.edge.fieldRoute')" required>
          <el-input v-model="form.route" :placeholder="$t('admin.system.edge.routePlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.edge.fieldCacheTtl')">
          <el-input-number v-model="form.cache_ttl" :max="86400" :min="0" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.edge.fieldDescription')">
          <el-input v-model="form.description" :maxlength="500"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.edge.fieldEnabled')">
          <el-switch v-model="form.enabled"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.edge.fieldCode')">
          <el-input
            v-model="form.code"
            :autosize="{minRows: 6, maxRows: 20}"
            :placeholder="$t('admin.system.edge.codePlaceholder')"
            type="textarea"
          />
          <p class="hint">{{ $t('admin.system.edge.codeHint') }}</p>
        </el-form-item>
      </el-form>

      <!-- 静态校验结果 -->
      <template v-if="validation">
        <el-divider>{{ $t('admin.system.edge.validationSection') }}</el-divider>
        <el-alert
          :closable="false"
          :title="validation.valid
            ? $t('admin.system.edge.validatedOk')
            : $t('admin.system.edge.validatedFail')"
          :type="validation.valid ? 'success' : 'error'"
          class="mb-2"
          show-icon
        />
        <p class="hint mb-2">
          {{ $t('admin.system.edge.validationSize', {size: validation.byte_size, limit: validation.size_limit}) }}
        </p>
        <el-table v-if="validation.checks.length" :data="validation.checks" border size="small">
          <el-table-column :label="$t('admin.system.edge.colRule')" prop="rule" width="150"/>
          <el-table-column :label="$t('admin.system.edge.colSeverity')" width="110">
            <template #default="{ row }">
              <el-tag :type="severityType((row as { severity: string }).severity)" size="small">
                {{ (row as { severity: string }).severity }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.system.edge.colMessage')" min-width="240" prop="message"/>
        </el-table>
        <p v-else class="hint">{{ $t('admin.system.edge.validationNoIssues') }}</p>
      </template>

      <template #footer>
        <el-button @click="drawerVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button
          v-auth="'module_system:integration:edit'"
          :disabled="!editing"
          :loading="validating"
          @click="onValidate"
        >
          {{ $t('admin.system.edge.validate') }}
        </el-button>
        <el-button
          v-auth="'module_system:integration:create'"
          :disabled="editing"
          :loading="saving"
          type="primary"
          @click="onSave"
        >
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-drawer>

    <!-- 部署结果（如实展示 reasason / 所需环境变量） -->
    <el-dialog
      v-model="deployVisible"
      :title="$t('admin.system.edge.deployResultSection')"
      width="600px"
    >
      <template v-if="deployResult">
        <el-alert
          :closable="false"
          :title="deployResult.deployed
            ? $t('admin.system.edge.deploySuccess')
            : $t('admin.system.edge.deployNotDeployed')"
          :type="deployResult.deployed ? 'success' : 'warning'"
          class="mb-3"
          show-icon
        />
        <div class="mgrid">
          <div class="mgrid__item">
            <span class="mgrid__label">{{ $t('admin.system.edge.colName') }}</span>
            <span class="mgrid__value">{{ deployResult.name }}</span>
          </div>
          <div class="mgrid__item">
            <span class="mgrid__label">{{ $t('admin.system.edge.colPlatform') }}</span>
            <span class="mgrid__value">{{ platformLabel(deployResult.platform) }}</span>
          </div>
          <div class="mgrid__item mgrid__item--wide">
            <span class="mgrid__label">{{ $t('admin.system.edge.deployReason') }}</span>
            <span class="mgrid__value">{{ deployResult.reason || '-' }}</span>
          </div>
          <div v-if="requiredEnv.length" class="mgrid__item mgrid__item--wide">
            <span class="mgrid__label">{{ $t('admin.system.edge.deployRequiredEnv') }}</span>
            <span class="mgrid__value">{{ requiredEnv.join(', ') }}</span>
          </div>
          <div v-if="deployResult.hint" class="mgrid__item mgrid__item--wide">
            <span class="mgrid__label">{{ $t('admin.system.edge.deployHint') }}</span>
            <span class="mgrid__value">{{ deployResult.hint }}</span>
          </div>
        </div>
        <pre
          v-if="deployResult.deployed && deployResult.remote"
          class="json-block"
        >{{ JSON.stringify(deployResult.remote, null, 2) }}</pre>
      </template>
    </el-dialog>

    <!-- 操作 / 部署日志（本地记录） -->
    <el-drawer v-model="logVisible" :title="$t('admin.system.edge.logTitle')" size="720px">
      <el-alert
        :closable="false"
        :title="$t('admin.system.edge.logIntro')"
        class="mb-3"
        show-icon
        type="info"
      />
      <template v-if="logResult">
        <div class="mgrid mb-3">
          <div class="mgrid__item">
            <span class="mgrid__label">{{ $t('admin.system.edge.colName') }}</span>
            <span class="mgrid__value">{{ logResult.name }}</span>
          </div>
          <div class="mgrid__item">
            <span class="mgrid__label">{{ $t('admin.system.edge.logSource') }}</span>
            <span class="mgrid__value">{{ logResult.source }} · remote={{ logResult.remote }}</span>
          </div>
          <div v-if="logResult.reason" class="mgrid__item mgrid__item--wide">
            <span class="mgrid__label">{{ $t('admin.system.edge.logReasonLabel') }}</span>
            <span class="mgrid__value">{{ logResult.reason }}</span>
          </div>
        </div>

        <el-table
          v-if="logResult.entries.length"
          v-loading="logLoading"
          :data="logResult.entries"
          border
          size="small"
          stripe
        >
          <el-table-column :label="$t('admin.system.edge.colLogAt')" min-width="170" prop="at"/>
          <el-table-column :label="$t('admin.system.edge.colLogMode')" prop="mode" width="120"/>
          <el-table-column :label="$t('admin.system.edge.colLogDeployed')" align="center" width="110">
            <template #default="{ row }">
              <el-tag :type="(row as EdgeDeployLogEntry).deployed ? 'success' : 'info'" size="small">
                {{ (row as EdgeDeployLogEntry).deployed ? $t('admin.common.yes') : $t('admin.common.no') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.system.edge.colLogReason')" min-width="200" prop="reason"
                           show-overflow-tooltip/>
        </el-table>
        <el-empty v-else :description="$t('admin.system.edge.logEmpty')" :image-size="60"/>
      </template>
      <el-empty v-else :description="$t('admin.system.edge.logEmpty')" :image-size="60"/>
    </el-drawer>
  </AdminPage>
</template>

<style scoped>
.mcard {
  padding: 16px 18px;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-line, #e5e7eb);
  border-radius: 8px;
}

.mcard__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.mcard__title {
  font-size: 15px;
  font-weight: 600;
}

.mgrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px 20px;
}

.mgrid__item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mgrid__item--wide {
  grid-column: 1 / -1;
}

.mgrid__label {
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.mgrid__value {
  font-size: 14px;
  color: var(--color-fg, #303133);
  word-break: break-all;
}

.hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.json-block {
  margin: 12px 0 0;
  padding: 10px 12px;
  overflow: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  background: var(--color-surface-soft, #f5f7fa);
  border-radius: 4px;
}

.mb-2 {
  margin-bottom: 8px;
}

.mb-3 {
  margin-bottom: 16px;
}
</style>
