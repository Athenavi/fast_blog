<script lang="ts" setup>
const {t} = useI18n()
/**
 * 主题管理
 *
 * 对齐 v3 `/extension/theme`：当前主题信息、配置读写、设置 schema、
 * 组件槽位契约、前台注入的 CSS。
 *
 * 配置项以 JSON 提交：后端 `ThemeConfigUpdate` 只接受受支持的键，
 * 主题实现不支持的槽位会被忽略并记录告警。
 */
import {Check, Refresh} from '@element-plus/icons-vue'
import {ElMessage} from '@/utils/feedback'
import {computed, ref} from 'vue'

import {themeApi, type ThemeConfig, type ThemeInfo} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.extension.theme.themes',
  permission: 'module_extension:theme:view',
})

const loading = ref(false)
const active = ref<ThemeInfo | null>(null)
const config = ref<ThemeConfig | null>(null)
const schema = ref<Record<string, unknown> | null>(null)
const contract = ref<Record<string, unknown> | null>(null)
const publicCss = ref('')

const settingsText = ref('{}')
const slotsText = ref('{}')
const saving = ref(false)

/** 从 settings_schema 里提取字段清单，用于给出可视化提示 */
const schemaFields = computed<Array<{ key: string; type: string; label: string }>>(() => {
  const raw = schema.value?.settings_schema
  if (!raw || typeof raw !== 'object') return []
  const props = (raw as { properties?: Record<string, Record<string, unknown>> }).properties
  if (!props || typeof props !== 'object') return []
  return Object.entries(props).map(([key, value]) => ({
    key,
    type: String(value?.type ?? 'unknown'),
    label: String(value?.title ?? value?.description ?? ''),
  }))
})

async function loadAll(): Promise<void> {
  loading.value = true
  try {
    const [info, cfg] = await Promise.all([
      themeApi.active().catch(() => null),
      themeApi.config().catch(() => null),
    ])
    active.value = info
    config.value = cfg
    settingsText.value = JSON.stringify(cfg?.settings ?? {}, null, 2)
    slotsText.value = JSON.stringify(cfg?.component_slots ?? {}, null, 2)

    const [sc, ct, css] = await Promise.all([
      themeApi.schema().catch(() => null),
      themeApi.contract().catch(() => null),
      themeApi.publicCss().catch(() => null),
    ])
    schema.value = sc
    contract.value = ct
    publicCss.value = css?.css ?? ''
  } finally {
    loading.value = false
  }
}

async function save(): Promise<void> {
  let settings: Record<string, unknown> = {}
  let slots: Record<string, unknown> = {}

  try {
    const parsedSettings = settingsText.value.trim() ? JSON.parse(settingsText.value) : {}
    if (parsedSettings === null || typeof parsedSettings !== 'object' || Array.isArray(parsedSettings)) {
      throw new Error(t('admin.extension.theme.settingsMustBeAJsonObject'))
    }
    settings = parsedSettings as Record<string, unknown>

    const parsedSlots = slotsText.value.trim() ? JSON.parse(slotsText.value) : {}
    if (parsedSlots === null || typeof parsedSlots !== 'object' || Array.isArray(parsedSlots)) {
      throw new Error(t('admin.extension.theme.componentSlotsMustBeAJsonObject'))
    }
    slots = parsedSlots as Record<string, unknown>
  } catch (error) {
    ElMessage.warning(t('admin.extension.theme.jsonParseFailed', {message: (error as Error).message}))
    return
  }

  saving.value = true
  try {
    const result = await themeApi.saveConfig(settings, slots)
    config.value = result
    ElMessage.success(t('admin.extension.theme.themeConfigurationSaved'))
  } finally {
    saving.value = false
  }
}

onMounted(loadAll)
</script>

<template>
  <div class="page-container">
    <el-row :gutter="16">
      <!-- 当前主题 -->
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>{{ $t('admin.extension.theme.currentTheme') }}</span>
              <el-button :icon="Refresh" link @click="loadAll"/>
            </div>
          </template>

          <div v-loading="loading">
            <div v-if="active" class="theme">
              <img v-if="active.screenshot" :alt="$t('admin.extension.theme.themeScreenshot')"
                   :src="String(active.screenshot)" class="theme__shot" decoding="async">
              <div v-else class="theme__placeholder">{{ $t('admin.extension.theme.noPreviewImage') }}</div>

              <p class="theme__name">{{ active.name || active.slug }}</p>
              <p class="theme__meta">
                v{{ active.version || '-' }}
                <span v-if="active.author"> · {{ active.author }}</span>
              </p>
              <p v-if="active.description" class="theme__desc">{{ active.description }}</p>
              <el-tag class="mt-2" size="small" type="success">{{ $t('admin.extension.theme.inUse') }}</el-tag>
            </div>
            <el-empty v-else :description="$t('admin.extension.theme.unableToReadTheCurrentTheme')"/>
          </div>
        </el-card>

        <!-- schema 字段提示 -->
        <el-card class="mt-4" shadow="never">
          <template #header><span>{{ $t('admin.extension.theme.availableSettings') }}</span></template>
          <el-table v-if="schemaFields.length" :data="schemaFields" border size="small">
            <el-table-column :label="$t('admin.extension.theme.key')" min-width="120" prop="key"/>
            <el-table-column :label="$t('admin.cache.level')" prop="type" width="90"/>
            <el-table-column :label="$t('admin.extension.theme.description')" min-width="140" prop="label"
                             show-overflow-tooltip/>
          </el-table>
          <el-empty v-else :description="$t('admin.extension.theme.thisThemeDeclaresNoSettings')"/>
        </el-card>
      </el-col>

      <!-- 配置 -->
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>{{ $t('admin.extension.theme.themeConfiguration') }}</span>
              <el-button
                v-auth="'module_extension:theme:customize'"
                :icon="Check"
                :loading="saving"
                type="primary"
                @click="save"
              >
                {{ $t('admin.common.save') }}
              </el-button>
            </div>
          </template>

          <el-form label-position="top">
            <el-form-item :label="$t('admin.extension.theme.settingsJson')">
              <el-input v-model="settingsText" :rows="10" placeholder='{ "accent": "blue" }' type="textarea"/>
            </el-form-item>
            <el-form-item :label="$t('admin.extension.theme.componentSlotMappingJsonOptional')">
              <el-input v-model="slotsText" :rows="6" placeholder='{ "sidebar": ["recent-posts"] }' type="textarea"/>
            </el-form-item>
          </el-form>

          <el-alert
            :closable="false"
            :title="$t('admin.extension.theme.unsupportedSlotsAreIgnoredAndLoggedSavingWillStillSucceed')"
            type="info"
          />
        </el-card>

        <!-- 契约与 CSS -->
        <el-card class="mt-4" shadow="never">
          <template #header><span>{{ $t('admin.extension.theme.componentSlotContractAndFrontendCss') }}</span>
          </template>
          <el-collapse>
            <el-collapse-item :title="$t('admin.extension.theme.componentSlotContract')" name="contract">
              <pre class="code">{{ JSON.stringify(contract ?? {}, null, 2) }}</pre>
            </el-collapse-item>
            <el-collapse-item :title="$t('admin.extension.theme.frontendInjectedCss')" name="css">
              <pre class="code">{{ publicCss || t('admin.extension.theme.thisThemeDoesNotProvideCustomCss') }}</pre>
            </el-collapse-item>
          </el-collapse>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.theme__shot,
.theme__placeholder {
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}

.theme__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
}

.theme__name {
  margin: 12px 0 0;
  font-size: 15px;
  font-weight: 600;
}

.theme__meta {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.theme__desc {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-regular);
}

.code {
  max-height: 320px;
  margin: 0;
  padding: 10px;
  overflow: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  line-height: 1.7;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.mt-2 {
  margin-top: 8px;
}

.mt-4 {
  margin-top: 16px;
}
</style>
