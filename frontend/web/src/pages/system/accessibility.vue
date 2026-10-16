<script lang="ts" setup>
/**
 * 无障碍设置（WCAG 2.1，system 域）
 *
 * 对齐 v3 `/system/accessibility` 的 8 个端点：
 *  - 配置读写（config）：落 `system_settings`，读公开、写需 `module_system:setting:edit`；
 *  - 纯生成：css / skip-links / shortcuts / aria / guide（公开）；
 *  - HTML 校验（validate）：按元素解析，需 `module_content:article:edit`。
 *
 * 页面分三个标签页：
 *  1. 配置：开关 / 字号 + 保存 + 生成的样式表预览；
 *  2. HTML 校验：粘贴 HTML → 展示规则 / 严重级别 / 评分；
 *  3. 指南与工具：使用指南 + 键盘快捷键 + 跳过链接 + ARIA 建议。
 */
import {ElMessage} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {
  accessibilityApi,
  type AccessibilityConfig,
  type AccessibilityGuide,
  type AccessibilityShortcut,
  type AccessibilitySkipLink,
  type AccessibilityValidationResult,
  type AccessibilityViolation,
  type AriaSuggestion,
} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.accessibility.title',
  permission: 'module_system:setting:view',
})

const {t} = useI18n()
const activeTab = ref('config')

// ---------------------------------------------------------------- 配置
type BooleanConfigKey =
  | 'keyboard_navigation'
  | 'screen_reader_support'
  | 'high_contrast_mode'
  | 'reduce_motion'
  | 'focus_visible'
  | 'skip_links'

const FONT_SIZES = ['small', 'medium', 'large', 'x-large'] as const
const FONT_SIZE_LABELS: Record<string, string> = {
  small: 'admin.system.accessibility.fontSizeSmall',
  medium: 'admin.system.accessibility.fontSizeMedium',
  large: 'admin.system.accessibility.fontSizeLarge',
  'x-large': 'admin.system.accessibility.fontSizeXLarge',
}

/** 布尔开关：label / hint 均为 i18n key（默认值对齐后端 DEFAULT_CONFIG） */
const BOOLEAN_FIELDS: { key: BooleanConfigKey; label: string; hint: string }[] = [
  {
    key: 'keyboard_navigation',
    label: 'admin.system.accessibility.keyboardNavigation',
    hint: 'admin.system.accessibility.keyboardNavigationHint',
  },
  {
    key: 'screen_reader_support',
    label: 'admin.system.accessibility.screenReaderSupport',
    hint: 'admin.system.accessibility.screenReaderSupportHint',
  },
  {
    key: 'high_contrast_mode',
    label: 'admin.system.accessibility.highContrastMode',
    hint: 'admin.system.accessibility.highContrastModeHint',
  },
  {
    key: 'reduce_motion',
    label: 'admin.system.accessibility.reduceMotion',
    hint: 'admin.system.accessibility.reduceMotionHint',
  },
  {
    key: 'focus_visible',
    label: 'admin.system.accessibility.focusVisible',
    hint: 'admin.system.accessibility.focusVisibleHint',
  },
  {
    key: 'skip_links',
    label: 'admin.system.accessibility.skipLinks',
    hint: 'admin.system.accessibility.skipLinksHint',
  },
]

const configLoading = ref(false)
const configSaving = ref(false)
const form = reactive<AccessibilityConfig>({
  keyboard_navigation: true,
  screen_reader_support: true,
  high_contrast_mode: false,
  font_size: 'medium',
  reduce_motion: false,
  focus_visible: true,
  skip_links: true,
})

function fontSizeLabel(size: string): string {
  return t(FONT_SIZE_LABELS[size] ?? size)
}

async function loadConfig(): Promise<void> {
  configLoading.value = true
  try {
    const data = await accessibilityApi.getConfig()
    Object.assign(form, data)
  } finally {
    configLoading.value = false
  }
}

async function saveConfig(): Promise<void> {
  configSaving.value = true
  try {
    // 提交全部已知键（后端按 DEFAULT_CONFIG 合并，未知键会被拒绝）
    const data = await accessibilityApi.saveConfig({...form})
    Object.assign(form, data)
    ElMessage.success(t('admin.system.accessibility.saved'))
    await loadCss()
  } finally {
    configSaving.value = false
  }
}

// ---------------------------------------------------------------- 样式表预览
const cssPreview = ref('')
const cssLoading = ref(false)

async function loadCss(): Promise<void> {
  cssLoading.value = true
  try {
    const data = await accessibilityApi.getCss()
    cssPreview.value = data.css
  } finally {
    cssLoading.value = false
  }
}

// ---------------------------------------------------------------- HTML 校验
const validateHtml = ref('')
const validating = ref(false)
const validation = ref<AccessibilityValidationResult | null>(null)

const allViolations = computed<AccessibilityViolation[]>(() => {
  const result = validation.value
  if (!result) return []
  return [...result.errors, ...result.warnings, ...result.infos]
})

function severityTag(severity: string): 'danger' | 'warning' | 'info' {
  if (severity === 'critical' || severity === 'serious') return 'danger'
  if (severity === 'moderate') return 'warning'
  return 'info'
}

async function runValidate(): Promise<void> {
  if (!validateHtml.value.trim()) {
    ElMessage.warning(t('admin.system.accessibility.htmlRequired'))
    return
  }
  validating.value = true
  try {
    validation.value = await accessibilityApi.validate(validateHtml.value)
  } finally {
    validating.value = false
  }
}

// ---------------------------------------------------------------- 指南与工具
const guide = ref<AccessibilityGuide | null>(null)
const guideLoading = ref(false)
const shortcuts = ref<AccessibilityShortcut[]>([])
const skipLinks = ref<AccessibilitySkipLink[]>([])

async function loadGuide(): Promise<void> {
  guideLoading.value = true
  try {
    guide.value = await accessibilityApi.guide()
  } finally {
    guideLoading.value = false
  }
}

async function loadShortcuts(): Promise<void> {
  shortcuts.value = await accessibilityApi.shortcuts()
}

async function loadSkipLinks(): Promise<void> {
  skipLinks.value = await accessibilityApi.skipLinks()
}

// ---- ARIA 建议（公开端点）
const ARIA_ELEMENTS = [
  'button',
  'link',
  'navigation',
  'search',
  'form',
  'dialog',
  'tab',
  'alert',
  'progressbar',
  'menu',
] as const

const ariaElementType = ref<string>('navigation')
const ariaContextLabel = ref('')
const ariaLoading = ref(false)
const ariaResult = ref<AriaSuggestion | null>(null)

const ariaRows = computed(() => {
  const attrs = ariaResult.value?.attributes ?? {}
  return Object.entries(attrs).map(([name, value]) => ({name, value}))
})

async function runAria(): Promise<void> {
  ariaLoading.value = true
  try {
    const context: Record<string, unknown> = {}
    const label = ariaContextLabel.value.trim()
    if (label) context.label = label
    ariaResult.value = await accessibilityApi.aria(ariaElementType.value, context)
  } finally {
    ariaLoading.value = false
  }
}

onMounted(() => {
  // 全部是只读加载：失败由 request 拦截器统一提示，这里只保证不产生未处理拒绝
  void Promise.allSettled([
    loadConfig(),
    loadCss(),
    loadGuide(),
    loadShortcuts(),
    loadSkipLinks(),
  ])
})
</script>

<template>
  <AdminPage :desc="$t('admin.system.accessibility.desc')" :title="$t('admin.system.accessibility.title')">
    <template #actions>
      <el-button
        v-if="activeTab === 'config'"
        v-auth="'module_system:setting:edit'"
        :loading="configSaving"
        type="primary"
        @click="saveConfig"
      >
        {{ $t('admin.system.accessibility.save') }}
      </el-button>
    </template>

    <el-tabs v-model="activeTab">
      <!-- 配置 -->
      <el-tab-pane :label="$t('admin.system.accessibility.tabConfig')" name="config">
        <el-form v-loading="configLoading" label-width="150px" style="max-width: 720px">
          <el-form-item v-for="field in BOOLEAN_FIELDS" :key="field.key" :label="$t(field.label)">
            <el-switch v-model="form[field.key]"/>
            <span class="a11y-hint">{{ $t(field.hint) }}</span>
          </el-form-item>
          <el-form-item :label="$t('admin.system.accessibility.fontSize')">
            <el-select v-model="form.font_size" style="width: 200px">
              <el-option v-for="size in FONT_SIZES" :key="size" :label="fontSizeLabel(size)" :value="size"/>
            </el-select>
          </el-form-item>
        </el-form>

        <div class="a11y-css">
          <div class="a11y-css__head">
            <span class="a11y-css__title">{{ $t('admin.system.accessibility.cssPreview') }}</span>
            <el-button :loading="cssLoading" link type="primary" @click="loadCss">
              {{ $t('admin.system.accessibility.regenerate') }}
            </el-button>
          </div>
          <pre v-if="cssPreview" class="a11y-css__body">{{ cssPreview }}</pre>
          <p v-else class="a11y-hint">{{ $t('admin.system.accessibility.cssEmpty') }}</p>
        </div>
      </el-tab-pane>

      <!-- HTML 校验 -->
      <el-tab-pane :label="$t('admin.system.accessibility.tabValidate')" name="validate">
        <el-form label-position="top">
          <el-form-item :label="$t('admin.system.accessibility.htmlLabel')">
            <el-input
              v-model="validateHtml"
              :autosize="{minRows: 8, maxRows: 18}"
              :placeholder="$t('admin.system.accessibility.htmlPlaceholder')"
              type="textarea"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              v-auth="'module_content:article:edit'"
              :loading="validating"
              type="primary"
              @click="runValidate"
            >
              {{ $t('admin.system.accessibility.validateBtn') }}
            </el-button>
          </el-form-item>
        </el-form>

        <template v-if="validation">
          <div class="a11y-score">
            <el-tag :type="validation.valid ? 'success' : 'danger'" size="large">
              {{ validation.valid ? $t('admin.system.accessibility.valid') : $t('admin.system.accessibility.invalid') }}
            </el-tag>
            <span class="a11y-score__item">
              {{ $t('admin.system.accessibility.score') }}: {{ validation.score }}
            </span>
            <span class="a11y-score__item">
              {{
                $t('admin.system.accessibility.summary', {
                  errors: validation.summary.errors,
                  warnings: validation.summary.warnings,
                  infos: validation.summary.infos,
                  elements: validation.summary.elements_checked,
                })
              }}
            </span>
          </div>

          <el-table v-if="allViolations.length" :data="allViolations" border stripe>
            <el-table-column :label="$t('admin.system.accessibility.severity')" width="120">
              <template #default="{ row }">
                <el-tag :type="severityTag((row as AccessibilityViolation).severity)" size="small">
                  {{ (row as AccessibilityViolation).severity }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.system.accessibility.rule')" min-width="150" prop="rule"/>
            <el-table-column :label="$t('admin.system.accessibility.message')" min-width="240" prop="message"/>
            <el-table-column
              :label="$t('admin.system.accessibility.snippet')"
              min-width="160"
              prop="snippet"
              show-overflow-tooltip
            />
          </el-table>
          <el-empty v-else :description="$t('admin.system.accessibility.noViolations')"/>
        </template>
      </el-tab-pane>

      <!-- 指南与工具 -->
      <el-tab-pane :label="$t('admin.system.accessibility.tabGuide')" name="guide">
        <div v-loading="guideLoading" class="a11y-guide">
          <el-alert
            v-if="guide"
            :closable="false"
            :title="$t('admin.system.accessibility.standard') + '：' + guide.standard"
            show-icon
            type="info"
          />
          <div v-if="guide" class="a11y-features">
            <div v-for="feature in guide.features" :key="feature.key" class="a11y-feature">
              <div class="a11y-feature__label">{{ feature.label }}</div>
              <div class="a11y-feature__hint">{{ feature.hint }}</div>
              <code class="a11y-feature__key">{{ feature.key }}</code>
            </div>
          </div>
        </div>

        <div class="a11y-grid">
          <section class="a11y-block">
            <h3 class="a11y-block__title">{{ $t('admin.system.accessibility.shortcuts') }}</h3>
            <el-table :data="shortcuts" border size="small">
              <el-table-column :label="$t('admin.system.accessibility.keys')" prop="keys" width="160"/>
              <el-table-column :label="$t('admin.system.accessibility.action')" prop="action"/>
            </el-table>
          </section>

          <section class="a11y-block">
            <h3 class="a11y-block__title">{{ $t('admin.system.accessibility.skipLinks') }}</h3>
            <el-table :data="skipLinks" border size="small">
              <el-table-column :label="$t('admin.system.accessibility.skipLinkText')" prop="text" width="120"/>
              <el-table-column :label="$t('admin.system.accessibility.skipLinkTarget')" prop="target"/>
              <el-table-column :label="$t('admin.system.accessibility.skipLinkAriaLabel')" prop="aria_label"/>
            </el-table>
          </section>
        </div>

        <section class="a11y-block">
          <h3 class="a11y-block__title">{{ $t('admin.system.accessibility.ariaTool') }}</h3>
          <el-form :inline="true">
            <el-form-item :label="$t('admin.system.accessibility.ariaElementType')">
              <el-select v-model="ariaElementType" style="width: 180px">
                <el-option v-for="el in ARIA_ELEMENTS" :key="el" :label="el" :value="el"/>
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('admin.system.accessibility.ariaContextLabel')">
              <el-input
                v-model="ariaContextLabel"
                :placeholder="$t('admin.system.accessibility.ariaContextPlaceholder')"
                clearable
                style="width: 220px"
              />
            </el-form-item>
            <el-form-item>
              <el-button :loading="ariaLoading" type="primary" @click="runAria">
                {{ $t('admin.system.accessibility.ariaGenerate') }}
              </el-button>
            </el-form-item>
          </el-form>
          <el-table v-if="ariaRows.length" :data="ariaRows" border size="small" style="max-width: 520px">
            <el-table-column :label="$t('admin.system.accessibility.attribute')" prop="name" width="200"/>
            <el-table-column :label="$t('admin.system.accessibility.value')" prop="value"/>
          </el-table>
          <p v-else class="a11y-hint">{{ $t('admin.system.accessibility.ariaEmpty') }}</p>
        </section>
      </el-tab-pane>
    </el-tabs>
  </AdminPage>
</template>

<style scoped>
.a11y-hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--color-fg-subtle);
}

.a11y-css {
  margin-top: 16px;
}

.a11y-css__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.a11y-css__title {
  font-weight: 600;
}

.a11y-css__body {
  max-height: 320px;
  padding: 12px;
  margin: 0;
  overflow: auto;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre;
  background: var(--color-surface-soft);
  border-radius: 6px;
}

.a11y-score {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.a11y-score__item {
  font-size: 13px;
  color: var(--color-fg-muted);
}

.a11y-guide {
  min-height: 60px;
  margin-bottom: 16px;
}

.a11y-features {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.a11y-feature {
  padding: 12px;
  border: 1px solid var(--color-border, #e4e7ed);
  border-radius: 8px;
}

.a11y-feature__label {
  font-weight: 600;
}

.a11y-feature__hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-fg-muted);
}

.a11y-feature__key {
  display: inline-block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-fg-subtle);
}

.a11y-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.a11y-block {
  margin-bottom: 16px;
}

.a11y-block__title {
  margin: 0 0 8px;
  font-size: 14px;
}
</style>
