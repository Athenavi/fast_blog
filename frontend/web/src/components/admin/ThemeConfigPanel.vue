<script lang="ts" setup>
const {t} = useI18n()
import {computed, onMounted, ref} from 'vue'

import {ElMessage} from '@/utils/feedback'
import {legacyGet, legacyPut} from '@/utils/legacyApi'

/**
 * 主题配置面板（三个主题插件共用）
 *
 * 对应 astro 的 `components/plugins/ThemeConfigPanel.tsx`：
 * 读主题的 `settings_schema` 渲染表单，再叠加「组件槽位」（header / articleCard / footer）选择，
 * 一并保存到 **`/api/v3/extension/theme/{slug}/config`**（T5-10 已自 v2 收敛）。
 *
 * 原实现自带一个顶部通知条；这里改用与后台其它页一致的 `ElMessage`。
 */
interface FieldDef {
  label?: string
  type?: string
  default?: unknown
  options?: Array<{ value: string; label?: string }>
}

interface GroupDef {
  label?: string
  fields?: Record<string, FieldDef>
}

interface ThemeConfig {
  settings?: Record<string, unknown>
  settings_schema?: Record<string, GroupDef>
  contract?: { componentSlots?: Record<string, string> }
}

const props = defineProps<{
  pluginSlug: string
  themeName: string
  themeDescription?: string
}>()

/** 可供主题覆盖的组件与其变体（与 astro 版一致） */
const SLOT_DEFS = [
  {
    key: 'header',
    label: t('admin.shared.admin.ThemeConfigPanel.topNavigation'),
    options: [
      {value: 'floating', label: t('admin.shared.admin.ThemeConfigPanel.floatingPillDefault')},
      {value: 'classic', label: t('admin.shared.admin.ThemeConfigPanel.classicHeader')},
    ],
  },
  {
    key: 'articleCard',
    label: t('admin.shared.admin.ThemeConfigPanel.articleCard'),
    options: [
      {value: 'default', label: t('admin.shared.admin.ThemeConfigPanel.standardCardDefault')},
      {value: 'compact', label: t('admin.shared.admin.ThemeConfigPanel.compactCard')},
    ],
  },
  {
    key: 'footer',
    label: t('admin.shared.admin.ThemeConfigPanel.footer'),
    options: [
      {value: 'default', label: t('admin.shared.admin.ThemeConfigPanel.standardDefault')},
      {value: 'minimal', label: t('admin.shared.admin.ThemeConfigPanel.minimal')},
    ],
  },
]

const loading = ref(true)
const error = ref('')
const saving = ref(false)

const config = ref<ThemeConfig>({})
const settings = ref<Record<string, unknown>>({})
const componentSlots = ref<Record<string, string>>({})

const groups = computed(() => Object.entries(config.value.settings_schema ?? {}))

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const result = await legacyGet<ThemeConfig>(`/extension/theme/${props.pluginSlug}/config`)
    if (!result.success) error.value = result.error || t('admin.shared.admin.ThemeConfigPanel.failedToLoadThemeConfiguration')
    config.value = result.data ?? {}
    settings.value = {...(result.data?.settings ?? {})}
    componentSlots.value = {...(result.data?.contract?.componentSlots ?? {})}
  } finally {
    loading.value = false
  }
}

function fieldValue(key: string, field: FieldDef): unknown {
  return settings.value[key] ?? field.default
}

function updateField(key: string, value: unknown): void {
  settings.value = {...settings.value, [key]: value}
}

function updateSlot(key: string, value: string): void {
  componentSlots.value = {...componentSlots.value, [key]: value}
}

function reset(): void {
  settings.value = {...(config.value.settings ?? {})}
  componentSlots.value = {...(config.value.contract?.componentSlots ?? {})}
}

async function save(): Promise<void> {
  saving.value = true
  try {
    const result = await legacyPut(`/extension/theme/${props.pluginSlug}/config`, {
      settings: settings.value,
      component_slots: componentSlots.value,
    })
    if (result.success) ElMessage.success(t('admin.shared.admin.ThemeConfigPanel.themeConfigurationSaved'))
    else ElMessage.error(result.error || t('admin.shared.admin.ThemeConfigPanel.failedToSave'))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-8">
    <p v-if="error" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

    <!-- 主题信息 -->
    <div class="rounded-card border border-line bg-surface p-6">
      <div class="flex items-center gap-4">
        <span class="flex h-16 w-16 items-center justify-center rounded-card bg-primary-soft">
          <Icon class="h-8 w-8 text-primary" name="palette"/>
        </span>
        <div>
          <h2 class="text-xl font-semibold text-fg">{{ themeName }}</h2>
          <p v-if="themeDescription" class="text-sm text-fg-muted">{{ themeDescription }}</p>
        </div>
      </div>
    </div>

    <div v-if="loading" class="space-y-3">
      <Skeleton class="h-24 w-full"/>
      <Skeleton class="h-40 w-full"/>
    </div>

    <template v-else>
      <!-- 配置表单（按 settings_schema 渲染） -->
      <div v-if="groups.length" class="space-y-6 rounded-card border border-line bg-surface p-6">
        <div v-for="[groupKey, group] in groups" :key="groupKey">
          <h3 class="mb-4 text-lg font-medium text-fg">{{ group.label || groupKey }}</h3>

          <div class="space-y-4 pl-2">
            <div v-for="[fieldKey, field] in Object.entries(group.fields ?? {})" :key="fieldKey">
              <label class="mb-1 block text-sm font-medium text-fg">{{ field.label || fieldKey }}</label>

              <!-- color -->
              <div v-if="field.type === 'color'" class="flex items-center gap-3">
                <input
                  :value="(fieldValue(fieldKey, field) as string) || '#000000'"
                  class="h-10 w-10 cursor-pointer rounded border border-line"
                  type="color"
                  @input="updateField(fieldKey, ($event.target as HTMLInputElement).value)"
                >
                <el-input
                  :model-value="(fieldValue(fieldKey, field) as string) || ''"
                  class="flex-1"
                  @update:model-value="updateField(fieldKey, $event)"
                />
              </div>

              <!-- select -->
              <el-select
                v-else-if="field.type === 'select'"
                :model-value="(fieldValue(fieldKey, field) as string) || ''"
                class="w-full"
                @update:model-value="updateField(fieldKey, $event)"
              >
                <el-option
                  v-for="option in field.options ?? []"
                  :key="option.value"
                  :label="option.label || option.value"
                  :value="option.value"
                />
              </el-select>

              <!-- boolean -->
              <el-switch
                v-else-if="field.type === 'boolean'"
                :model-value="Boolean(fieldValue(fieldKey, field))"
                @update:model-value="updateField(fieldKey, $event)"
              />

              <!-- number -->
              <el-input
                v-else-if="field.type === 'number'"
                :model-value="String(fieldValue(fieldKey, field) ?? '')"
                type="number"
                @update:model-value="updateField(fieldKey, Number($event))"
              />

              <!-- textarea -->
              <el-input
                v-else-if="field.type === 'textarea'"
                :model-value="(fieldValue(fieldKey, field) as string) || ''"
                :rows="3"
                type="textarea"
                @update:model-value="updateField(fieldKey, $event)"
              />

              <!-- text（默认） -->
              <el-input
                v-else
                :model-value="(fieldValue(fieldKey, field) as string) || ''"
                @update:model-value="updateField(fieldKey, $event)"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 组件槽位 -->
      <div class="space-y-6 rounded-card border border-line bg-surface p-6">
        <div class="flex items-center gap-3">
          <Icon class="h-5 w-5 text-primary" name="layers"/>
          <h3 class="text-lg font-medium text-fg">{{ $t('admin.shared.admin.ThemeConfigPanel.component') }}</h3>
          <span class="text-xs text-fg-subtle">{{
              $t('admin.shared.admin.ThemeConfigPanel.chooseTheVariantUsedByEachComponentInThisTheme')
            }}</span>
        </div>

        <div class="space-y-4 pl-2">
          <div v-for="slot in SLOT_DEFS" :key="slot.key">
            <label class="mb-1 block text-sm font-medium text-fg">{{ slot.label }}</label>
            <el-select
              :model-value="componentSlots[slot.key] || slot.options[0]?.value || ''"
              class="w-full"
              @update:model-value="updateSlot(slot.key, $event)"
            >
              <el-option
                v-for="option in slot.options"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </div>
        </div>
      </div>

      <!-- 操作 -->
      <div class="flex justify-end gap-3">
        <el-button @click="reset">
          <Icon class="mr-1 h-4 w-4" name="rotate-ccw"/>
          {{ $t('admin.common.reset') }}
        </el-button>
        <el-button :loading="saving" type="primary" @click="save">
          <Icon class="mr-1 h-4 w-4" name="save"/>
          {{ $t('admin.shared.ThemeConfigPanel.saveConfig') }}
        </el-button>
      </div>
    </template>
  </div>
</template>
