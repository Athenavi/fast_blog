<script lang="ts" setup>
/**
 * 系统工具（/system/utilities）
 *
 * 对齐 v3 `/system/utility` 的零散能力：NLP 命令解析（含解析器能力目录）、
 * 区块模式定义展开、文章 Markdown 附件导出。NLP 两个端点公开，其余复用既有只读权限码。
 * 文章导出返回的是**流式附件**（非 JSON 信封），走 blob 下载范式。
 */
import {Refresh} from '@element-plus/icons-vue'
import {ElMessage} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {type BlockPatternDef, type NlpIntentCatalog, type NlpParseResult, utilityApi,} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.utility.title',
  permission: 'module_system:setting:view',
})

const {t} = useI18n()
const activeTab = ref('nlp')

// ---------------------------------------------------------------- 只读加载：NLP 能力目录
const catalog = ref<NlpIntentCatalog | null>(null)
const catalogLoading = ref(false)
const catalogFailed = ref(false)

/** 意图 → 触发关键词，供表格展示 */
const patternRows = computed(() =>
  Object.entries(catalog.value?.intent_patterns ?? {}).map(([intent, patterns]) => ({
    intent,
    patterns,
  })),
)

async function loadCatalog(): Promise<void> {
  catalogLoading.value = true
  catalogFailed.value = false
  // 只读加载统一用 allSettled：失败不抛出，交由 failed 标记渲染错误态
  const [res] = await Promise.allSettled([utilityApi.nlpIntents()])
  if (res.status === 'fulfilled') {
    catalog.value = res.value
  } else {
    catalogFailed.value = true
  }
  catalogLoading.value = false
}

// ---------------------------------------------------------------- NLP 命令解析
const parseForm = reactive<{ command: string }>({command: ''})
const parsing = ref(false)
const parseResult = ref<NlpParseResult | null>(null)

async function runParse(): Promise<void> {
  const command = parseForm.command.trim()
  if (!command) {
    ElMessage.warning(t('admin.system.utility.commandRequired'))
    return
  }
  parsing.value = true
  try {
    parseResult.value = await utilityApi.parseCommand(command)
  } finally {
    parsing.value = false
  }
}

async function copyResult(): Promise<void> {
  if (!import.meta.client || !parseResult.value) return
  try {
    await navigator.clipboard.writeText(JSON.stringify(parseResult.value, null, 2))
    ElMessage.success(t('admin.system.utility.copied'))
  } catch {
    // 剪贴板不可用：静默（非关键路径）
  }
}

// ---------------------------------------------------------------- 区块模式展开
const patternForm = reactive<{ id: number | undefined }>({id: undefined})
const patternLoading = ref(false)
const pattern = ref<BlockPatternDef | null>(null)

async function expandPattern(): Promise<void> {
  const id = patternForm.id
  if (!id || id <= 0) {
    ElMessage.warning(t('admin.system.utility.patternIdRequired'))
    return
  }
  patternLoading.value = true
  try {
    pattern.value = await utilityApi.blockPattern(id)
  } finally {
    patternLoading.value = false
  }
}

// ---------------------------------------------------------------- 文章 Markdown 导出
const exportForm = reactive<{ id: number | undefined; language: string; includeTitle: boolean }>({
  id: undefined,
  language: '',
  includeTitle: true,
})
const exporting = ref(false)

/** 从 Content-Disposition 解析文件名：先 RFC 6266 的 filename*=UTF-8''，再退回 filename */
function parseFilename(disposition: unknown, fallback: string): string {
  const header = typeof disposition === 'string' ? disposition : ''
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(header)
  if (utf8?.[1]) {
    try {
      return decodeURIComponent(utf8[1])
    } catch {
      return utf8[1]
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header)
  if (plain?.[1]) return plain[1]
  return fallback
}

/** 仅浏览器环境触发下载：createObjectURL + 临时 <a download> */
function triggerDownload(blob: Blob, filename: string): void {
  if (!import.meta.client) return
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

async function exportMarkdown(): Promise<void> {
  const id = exportForm.id
  if (!id || id <= 0) {
    ElMessage.warning(t('admin.system.utility.articleIdRequired'))
    return
  }
  exporting.value = true
  try {
    const resp = await utilityApi.articleMarkdown(id, {
      language: exportForm.language.trim() || undefined,
      include_title: exportForm.includeTitle,
    })
    const filename = parseFilename(resp.headers['content-disposition'], `blog_${id}.md`)
    triggerDownload(resp.data, filename)
    ElMessage.success(t('admin.system.utility.exportStarted'))
  } finally {
    exporting.value = false
  }
}

onMounted(loadCatalog)
</script>

<template>
  <AdminPage :desc="$t('admin.system.utility.desc')" :title="$t('admin.system.utility.title')">
    <template #actions>
      <el-button :icon="Refresh" :loading="catalogLoading" @click="loadCatalog">
        {{ $t('admin.common.refresh') }}
      </el-button>
    </template>

    <el-tabs v-model="activeTab">
      <!-- NLP 命令解析 -->
      <el-tab-pane :label="$t('admin.system.utility.tabNlp')" name="nlp">
        <el-alert
          v-if="catalogFailed"
          :closable="false"
          :title="$t('admin.common.loadFailed')"
          class="mb-3"
          show-icon
          type="error"
        />

        <section class="ucard mb-3">
          <div class="ucard__head">
            <span class="ucard__title">{{ $t('admin.system.utility.catalogTitle') }}</span>
          </div>
          <p class="hint mb-2">{{ $t('admin.system.utility.catalogHint') }}</p>
          <div v-if="catalog" class="mgrid">
            <div class="mgrid__item mgrid__item--wide">
              <span class="mgrid__label">{{ $t('admin.system.utility.intents') }}</span>
              <span class="mgrid__value">
                <el-tag
                  v-for="intent in catalog.intents"
                  :key="intent"
                  class="tag-gap"
                  size="small"
                >{{ intent }}</el-tag>
              </span>
            </div>
            <div class="mgrid__item mgrid__item--wide">
              <span class="mgrid__label">{{ $t('admin.system.utility.entityTypes') }}</span>
              <span class="mgrid__value">
                <el-tag
                  v-for="ent in catalog.entity_types"
                  :key="ent"
                  class="tag-gap"
                  size="small"
                  type="info"
                >{{ ent }}</el-tag>
              </span>
            </div>
            <div class="mgrid__item mgrid__item--wide">
              <span class="mgrid__label">{{ $t('admin.system.utility.timeRanges') }}</span>
              <span class="mgrid__value">
                <el-tag
                  v-for="tr in catalog.time_ranges"
                  :key="tr"
                  class="tag-gap"
                  size="small"
                  type="warning"
                >{{ tr }}</el-tag>
              </span>
            </div>
          </div>
          <el-empty v-else :description="$t('admin.system.utility.catalogEmpty')" :image-size="60"/>
        </section>

        <!-- 意图触发关键词 -->
        <section v-if="catalog" class="ucard mb-3">
          <div class="ucard__head">
            <span class="ucard__title">{{ $t('admin.system.utility.intentPatterns') }}</span>
          </div>
          <el-table :data="patternRows" border size="small" stripe>
            <el-table-column :label="$t('admin.system.utility.resultIntent')" prop="intent" width="180"/>
            <el-table-column :label="$t('admin.system.utility.keywordColumn')">
              <template #default="{ row }">
                <span>{{ (row.patterns || []).join('、') || '-' }}</span>
              </template>
            </el-table-column>
          </el-table>
        </section>

        <!-- 命令解析 -->
        <section class="ucard">
          <div class="ucard__head">
            <span class="ucard__title">{{ $t('admin.system.utility.parseSection') }}</span>
          </div>
          <p class="hint mb-2">{{ $t('admin.system.utility.parseHint') }}</p>
          <el-input
            v-model="parseForm.command"
            :maxlength="2000"
            :placeholder="$t('admin.system.utility.commandPlaceholder')"
            :rows="3"
            show-word-limit
            type="textarea"
          />
          <div class="actions-row">
            <el-button :loading="parsing" type="primary" @click="runParse">
              {{ $t('admin.system.utility.parseButton') }}
            </el-button>
          </div>

          <template v-if="parseResult">
            <el-descriptions :column="2" border class="mt-3">
              <el-descriptions-item :label="$t('admin.system.utility.resultIntent')">
                {{ parseResult.intent || $t('admin.system.utility.noIntent') }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('admin.system.utility.resultEntityType')">
                {{ parseResult.entity_type || '-' }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('admin.system.utility.resultConfidence')">
                {{ parseResult.confidence }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('admin.system.utility.resultTimestamp')">
                {{ parseResult.timestamp || '-' }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('admin.system.utility.resultError')" :span="2">
                <el-tag v-if="parseResult.error" size="small" type="danger">
                  {{ parseResult.error }}
                </el-tag>
                <span v-else>-</span>
              </el-descriptions-item>
            </el-descriptions>

            <div class="ucard__head mt-3">
              <span class="ucard__title">{{ $t('admin.system.utility.resultParameters') }}</span>
              <el-button link type="primary" @click="copyResult">
                {{ $t('admin.system.utility.copyResult') }}
              </el-button>
            </div>
            <pre class="json-block">{{ JSON.stringify(parseResult.parameters, null, 2) }}</pre>
          </template>
        </section>
      </el-tab-pane>

      <!-- 区块模式展开 -->
      <el-tab-pane :label="$t('admin.system.utility.tabBlockPattern')" name="blockPattern">
        <section class="ucard">
          <div class="ucard__head">
            <span class="ucard__title">{{ $t('admin.system.utility.patternSection') }}</span>
          </div>
          <p class="hint mb-2">{{ $t('admin.system.utility.patternHint') }}</p>
          <div class="actions-row">
            <el-input-number
              v-model="patternForm.id"
              :min="1"
              :placeholder="$t('admin.system.utility.patternIdPlaceholder')"
              style="width: 220px"
            />
            <el-button :loading="patternLoading" type="primary" @click="expandPattern">
              {{ $t('admin.system.utility.expandButton') }}
            </el-button>
          </div>

          <el-descriptions v-if="pattern" :column="2" border class="mt-3">
            <el-descriptions-item :label="$t('admin.system.utility.patternName')">
              {{ pattern.name || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.utility.patternTitle')">
              {{ pattern.title || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.utility.patternCategory')">
              {{ pattern.category || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.utility.patternViewportWidth')">
              {{ pattern.viewport_width ?? '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.utility.patternIsPublic')">
              {{ pattern.is_public ? $t('admin.common.yes') : $t('admin.common.no') }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.utility.patternThumbnail')">
              {{ pattern.thumbnail || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.utility.patternCreatedAt')">
              {{ pattern.created_at || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.utility.patternUpdatedAt')">
              {{ pattern.updated_at || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.utility.patternDescription')" :span="2">
              {{ pattern.description || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.utility.patternKeywords')" :span="2">
              <el-tag v-for="kw in pattern.keywords" :key="kw" class="tag-gap" size="small">
                {{ kw }}
              </el-tag>
              <span v-if="!pattern.keywords.length">-</span>
            </el-descriptions-item>
          </el-descriptions>

          <template v-if="pattern">
            <div class="ucard__head mt-3">
              <span class="ucard__title">{{ $t('admin.system.utility.patternBlocks') }}</span>
            </div>
            <pre class="json-block">{{ JSON.stringify(pattern.blocks, null, 2) }}</pre>
          </template>
        </section>
      </el-tab-pane>

      <!-- 文章 Markdown 导出 -->
      <el-tab-pane :label="$t('admin.system.utility.tabMarkdown')" name="markdown">
        <section class="ucard">
          <div class="ucard__head">
            <span class="ucard__title">{{ $t('admin.system.utility.exportSection') }}</span>
          </div>
          <p class="hint mb-2">{{ $t('admin.system.utility.exportHint') }}</p>
          <el-form :model="exportForm" label-width="150px">
            <el-form-item :label="$t('admin.system.utility.articleIdLabel')">
              <el-input-number v-model="exportForm.id" :min="1" style="width: 220px"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.utility.languageLabel')">
              <el-input
                v-model="exportForm.language"
                :placeholder="$t('admin.system.utility.languagePlaceholder')"
                clearable
                style="max-width: 220px"
              />
            </el-form-item>
            <el-form-item :label="$t('admin.system.utility.includeTitleLabel')">
              <el-switch v-model="exportForm.includeTitle"/>
            </el-form-item>
          </el-form>
          <div class="actions-row">
            <el-button :loading="exporting" type="primary" @click="exportMarkdown">
              {{ $t('admin.system.utility.exportButton') }}
            </el-button>
          </div>
        </section>
      </el-tab-pane>
    </el-tabs>
  </AdminPage>
</template>

<style scoped>
.ucard {
  padding: 16px 18px;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-line, #e5e7eb);
  border-radius: 8px;
}

.ucard__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.ucard__title {
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
  margin: 0;
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.actions-row {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.tag-gap {
  margin: 0 6px 6px 0;
}

.json-block {
  max-height: 360px;
  padding: 12px;
  margin: 0;
  overflow: auto;
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-fg-muted, #606266);
  background: var(--color-surface-soft, #f5f7fa);
  border-radius: 4px;
}

.mb-2 {
  margin-bottom: 8px;
}

.mb-3 {
  margin-bottom: 16px;
}

.mt-3 {
  margin-top: 16px;
}
</style>
