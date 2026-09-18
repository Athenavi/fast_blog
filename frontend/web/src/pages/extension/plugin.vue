<script lang="ts" setup>
const {t} = useI18n()
/**
 * 插件管理
 *
 * 对齐 v3 `/extension/plugin`：列表、扫描新插件、安装/激活/停用/卸载、配置。
 *
 * ⚠️ 安装、激活、停用、卸载都会改动运行环境，按既有约定需 `confirm=true`，
 * 这里统一走二次确认；卸载额外使用独立的 delete 权限码。
 */
import {Delete, Refresh, Setting, Upload} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {ref} from 'vue'

import {pluginApi, type PluginItem} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.extension.plugin.plugins',
  permission: 'module_extension:plugin:view',
})

const loading = ref(false)
const scanning = ref(false)
const list = ref<PluginItem[]>([])
const total = ref(0)

async function loadList(): Promise<void> {
  loading.value = true
  try {
    const data = await pluginApi.list()
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function scan(): Promise<void> {
  scanning.value = true
  try {
    const result = await pluginApi.scan()
    if (result?.count) {
      ElMessage.success(t('admin.extension.plugin.scanFound', {
        count: result.count,
        plugins: result.new_plugins.join('、')
      }))
    } else {
      ElMessage.info(t('admin.extension.plugin.noNewPluginsFound'))
    }
    await loadList()
  } finally {
    scanning.value = false
  }
}

/** 危险动作统一入口：确认 + 执行 + 刷新，并把后端返回的 detail 透出 */
async function act(
  row: PluginItem,
  action: 'install' | 'activate' | 'deactivate' | 'uninstall',
): Promise<void> {
  const slug = row.slug || ''
  if (!slug) return

  const LABELS = {
    install: t('admin.extension.plugin.install'),
    activate: t('admin.extension.plugin.activate'),
    deactivate: t('admin.common.disabled'),
    uninstall: t('admin.extension.plugin.uninstall')
  }
  const label = LABELS[action]
  const danger = action === 'uninstall'

  await ElMessageBox.confirm(
    danger ? t('admin.extension.plugin.uninstallConfirm', {name: row.name || slug}) : t('admin.extension.plugin.actionConfirm', {
      action: label,
      name: row.name || slug
    }),
    danger ? t('admin.extension.plugin.dangerousOperation') : t('admin.common.notice'),
    danger
      ? {
        type: 'error',
        confirmButtonText: t('admin.extension.plugin.confirmUninstall'),
        confirmButtonClass: 'el-button--danger'
      }
      : {type: 'warning'},
  )

  const result =
    action === 'install'
      ? await pluginApi.install(slug)
      : action === 'activate'
        ? await pluginApi.activate(slug)
        : action === 'deactivate'
          ? await pluginApi.deactivate(slug)
          : await pluginApi.uninstall(slug)

  if (result?.success === false) {
    ElMessage.error(result.detail || t('admin.extension.plugin.actionFailed', {action: label}))
  } else {
    ElMessage.success(t('admin.extension.plugin.actionSucceeded', {
      action: label,
      detail: result?.detail ? `：${result.detail}` : ''
    }))
  }
  await loadList()
}

// ---------------------------------------------------------------- 插件配置
const dialogVisible = ref(false)
const configSaving = ref(false)
const activePlugin = ref<PluginItem | null>(null)
const configText = ref('{}')

async function openSettings(row: PluginItem): Promise<void> {
  const slug = row.slug || ''
  if (!slug) return
  activePlugin.value = row
  configText.value = '{}'
  dialogVisible.value = true
  try {
    const data = await pluginApi.settings(slug)
    configText.value = JSON.stringify(data.settings ?? {}, null, 2)
  } catch {
    configText.value = '{}'
  }
}

async function saveSettings(): Promise<void> {
  const slug = activePlugin.value?.slug
  if (!slug) return

  let settings: Record<string, unknown> = {}
  try {
    const parsed = configText.value.trim() ? JSON.parse(configText.value) : {}
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error(t('admin.extension.plugin.mustBeAJsonObject'))
    }
    settings = parsed as Record<string, unknown>
  } catch (error) {
    ElMessage.warning(t('admin.common.configInvalidJson', {message: (error as Error).message}))
    return
  }

  configSaving.value = true
  try {
    await pluginApi.saveSettings(slug, settings)
    ElMessage.success(t('admin.extension.plugin.configurationSaved'))
    dialogVisible.value = false
  } finally {
    configSaving.value = false
  }
}

onMounted(loadList)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="toolbar">
        <el-button :icon="Refresh" :loading="scanning" @click="scan">{{
            $t('admin.extension.plugin.scanPlugins')
          }}
        </el-button>
        <span class="hint">{{
            $t('admin.extension.plugin.newPluginsInThePluginDirectoryMustBeScannedBeforeTheyAppearInTheList')
          }}</span>
        <el-button :icon="Refresh" circle class="ml-auto" @click="loadList"/>
      </div>

      <el-table v-loading="loading" :data="list" row-key="slug">
        <el-table-column :label="$t('admin.extension.plugin.plugins2')" min-width="240">
          <template #default="{row}">
            <div class="plugin">
              <span class="plugin__name">{{ row.name || row.slug }}</span>
              <span class="plugin__slug">{{ row.slug }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.extension.plugin.version')" prop="version" width="100"/>
        <el-table-column :label="$t('article.author')" prop="author" width="140"/>
        <el-table-column :label="$t('article.category')" prop="category" width="120"/>
        <el-table-column :label="$t('admin.common.status')" width="100">
          <template #default="{row}">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? t('admin.extension.plugin.active') : t('admin.extension.plugin.inactive') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="280">
          <template #default="{row}">
            <el-button
              v-auth="'module_extension:plugin:install'"
              :icon="Upload"
              link
              type="primary"
              @click="act(row, 'install')"
            >
              {{ $t('admin.extension.plugin.install') }}
            </el-button>
            <el-button
              v-if="!row.is_active"
              v-auth="'module_extension:plugin:activate'"
              link
              type="success"
              @click="act(row, 'activate')"
            >
              {{ $t('admin.extension.plugin.activate') }}
            </el-button>
            <el-button
              v-else
              v-auth="'module_extension:plugin:activate'"
              link
              type="warning"
              @click="act(row, 'deactivate')"
            >
              {{ $t('admin.common.disabled') }}
            </el-button>
            <el-button
              v-auth="'module_extension:plugin:configure'"
              :icon="Setting"
              link
              type="primary"
              @click="openSettings(row)"
            >
              {{ $t('admin.extension.plugin.configuration') }}
            </el-button>
            <el-button
              v-auth="'module_extension:plugin:delete'"
              :icon="Delete"
              link
              type="danger"
              @click="act(row, 'uninstall')"
            >
              {{ $t('admin.extension.plugin.uninstall') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <p class="hint">{{ $t('admin.extension.plugin.summary', {total}) }}</p>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="$t('admin.extension.plugin.configTitle', {name: activePlugin?.name || activePlugin?.slug || ''})"
      destroy-on-close
      width="640px"
    >
      <el-alert
        :closable="false"
        class="mb-3"
        :title="$t('admin.extension.plugin.submitConfigurationAsAJsonObjectSeeThePluginDocumentationForFieldMeanings')"
        type="info"
      />
      <el-input v-model="configText" :rows="12" placeholder='{ "key": "value" }' type="textarea"/>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="configSaving" type="primary" @click="saveSettings">{{
            $t('admin.common.save')
          }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.ml-auto {
  margin-left: auto;
}

.plugin {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.plugin__name {
  font-weight: 500;
}

.plugin__slug {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.mb-3 {
  margin-bottom: 12px;
}
</style>
