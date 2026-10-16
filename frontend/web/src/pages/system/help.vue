<script lang="ts" setup>
/**
 * 帮助中心（/system/help）
 *
 * 对齐后端 v3 `/system/help` 的 7 个端点：
 *   - 主题：概览列表（公开）/ 单条详情（公开）/ 新增覆盖 / 删除（需 setting:edit）；
 *   - 工具：相关性搜索（公开）+ 字段提示（公开）；
 *   - 教程：视频列表（公开，可按 topic 过滤）。
 *
 * 公开读端点无需权限即可加载；写操作按钮以 v-auth 收敛到 `module_system:setting:edit`。
 * 只读加载（主题 + 视频）用 Promise.allSettled，两个端点互不阻塞。
 */
import {Delete, Plus, Refresh, Search} from '@element-plus/icons-vue'
import {computed, onMounted, reactive, ref} from 'vue'

import {
  helpApi,
  type HelpRelatedLink,
  type HelpSearchItem,
  type HelpTooltipResult,
  type HelpTopicDetail,
  type HelpTopicSummary,
  type HelpVideoItem,
} from '@/api'
import AdminFormDrawer from '@/components/admin/AdminFormDrawer.vue'
import AdminListShell from '@/components/admin/AdminListShell.vue'
import AdminPage from '@/components/admin/AdminPage.vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {splitTags} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.help.title',
  permission: 'module_system:setting:view',
})

const {t} = useI18n()
const activeTab = ref('topics')

// ---------------------------------------------------------------- 只读数据：主题 / 视频
const topics = ref<HelpTopicSummary[]>([])
const topicsLoading = ref(false)
const topicsFailed = ref(false)

const videos = ref<HelpVideoItem[]>([])
const videosLoading = ref(false)
const videosFailed = ref(false)

/** 首次与刷新：两个公开端点并行，各自独立成败（Promise.allSettled） */
async function loadAll(): Promise<void> {
  topicsLoading.value = true
  videosLoading.value = true
  topicsFailed.value = false
  videosFailed.value = false
  const [topicsResult, videosResult] = await Promise.allSettled([
    helpApi.listTopics(),
    helpApi.videos(),
  ])
  if (topicsResult.status === 'fulfilled') topics.value = topicsResult.value
  else topicsFailed.value = true
  if (videosResult.status === 'fulfilled') videos.value = videosResult.value
  else videosFailed.value = true
  topicsLoading.value = false
  videosLoading.value = false
}

onMounted(loadAll)

// ---------------------------------------------------------------- 只读详情抽屉
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailTopic = ref<HelpTopicDetail | null>(null)

async function openView(row: HelpTopicSummary): Promise<void> {
  detailVisible.value = true
  detailTopic.value = null
  detailLoading.value = true
  try {
    detailTopic.value = await helpApi.getTopic(row.page_key)
  } finally {
    detailLoading.value = false
  }
}

// ---------------------------------------------------------------- 新建 / 覆盖抽屉
const formDrawerVisible = ref(false)
const formSaving = ref(false)
const formMode = ref<'create' | 'edit'>('create')
const topicForm = reactive({
  page_key: '',
  title: '',
  content: '',
  tagsText: '',
  language: 'zh_CN',
  relatedLinksText: '',
})

const formDrawerTitle = computed(() =>
  t(formMode.value === 'create' ? 'admin.system.help.createTopic' : 'admin.system.help.editTopic'),
)

function resetForm(): void {
  Object.assign(topicForm, {
    page_key: '',
    title: '',
    content: '',
    tagsText: '',
    language: 'zh_CN',
    relatedLinksText: '',
  })
}

function openCreate(): void {
  formMode.value = 'create'
  resetForm()
  formDrawerVisible.value = true
}

async function openEdit(row: HelpTopicSummary): Promise<void> {
  formMode.value = 'edit'
  resetForm()
  formDrawerVisible.value = true
  const detail = await helpApi.getTopic(row.page_key)
  topicForm.page_key = detail.page_key
  topicForm.title = detail.title
  topicForm.content = detail.content
  topicForm.tagsText = (detail.tags ?? []).join(', ')
  topicForm.language = detail.language || 'zh_CN'
  topicForm.relatedLinksText = detail.related_links?.length
    ? JSON.stringify(detail.related_links, null, 2)
    : ''
}

/** 解析相关链接输入（JSON 数组，元素含 title / url 两个字符串） */
function parseRelatedLinks(text: string): HelpRelatedLink[] {
  const trimmed = text.trim()
  if (!trimmed) return []
  const parsed: unknown = JSON.parse(trimmed)
  if (!Array.isArray(parsed)) throw new Error('related_links must be an array')
  return parsed.map((item) => {
    const link = item as Record<string, unknown>
    if (typeof link?.title !== 'string' || typeof link?.url !== 'string') {
      throw new Error('related_links items need title and url')
    }
    return {title: link.title, url: link.url}
  })
}

async function submitTopic(): Promise<void> {
  const pageKey = topicForm.page_key.trim()
  if (!pageKey) {
    ElMessage.warning(t('admin.system.help.requiredPageKey'))
    return
  }
  if (!topicForm.title.trim()) {
    ElMessage.warning(t('admin.system.help.requiredTitle'))
    return
  }
  if (!topicForm.content.trim()) {
    ElMessage.warning(t('admin.system.help.requiredContent'))
    return
  }
  let relatedLinks: HelpRelatedLink[]
  try {
    relatedLinks = parseRelatedLinks(topicForm.relatedLinksText)
  } catch {
    ElMessage.warning(t('admin.system.help.relatedLinksInvalid'))
    return
  }
  formSaving.value = true
  try {
    const result = await helpApi.upsertTopic({
      page_key: pageKey,
      title: topicForm.title.trim(),
      content: topicForm.content,
      tags: splitTags(topicForm.tagsText),
      language: topicForm.language,
      related_links: relatedLinks,
    })
    ElMessage.success(
      t(result.action === 'updated' ? 'admin.system.help.updated' : 'admin.system.help.created'),
    )
    formDrawerVisible.value = false
    await loadAll()
  } finally {
    formSaving.value = false
  }
}

async function removeTopic(row: HelpTopicSummary): Promise<void> {
  try {
    await ElMessageBox.confirm(
      t('admin.system.help.deleteConfirm', {name: row.title || row.page_key}),
      t('admin.common.notice'),
      {type: 'warning'},
    )
  } catch {
    return
  }
  await helpApi.deleteTopic(row.page_key)
  ElMessage.success(t('admin.system.help.deleted'))
  await loadAll()
}

// ---------------------------------------------------------------- 工具：相关性搜索
const searchForm = reactive({q: '', limit: 20})
const searchLoading = ref(false)
const searchDone = ref(false)
const searchResults = ref<HelpSearchItem[]>([])

async function runSearch(): Promise<void> {
  const q = searchForm.q.trim()
  if (!q) {
    ElMessage.warning(t('admin.system.help.searchRequired'))
    return
  }
  searchLoading.value = true
  try {
    searchResults.value = await helpApi.search({q, limit: searchForm.limit})
    searchDone.value = true
  } finally {
    searchLoading.value = false
  }
}

// ---------------------------------------------------------------- 工具：字段提示
const tooltipForm = reactive({field: '', context: 'general'})
const tooltipLoading = ref(false)
const tooltipResult = ref<HelpTooltipResult | null>(null)

async function runTooltip(): Promise<void> {
  const field = tooltipForm.field.trim()
  if (!field) {
    ElMessage.warning(t('admin.system.help.tooltipFieldRequired'))
    return
  }
  tooltipLoading.value = true
  try {
    tooltipResult.value = await helpApi.tooltip({
      field,
      context: tooltipForm.context.trim() || 'general',
    })
  } finally {
    tooltipLoading.value = false
  }
}

// ---------------------------------------------------------------- 视频过滤
const videoFilter = ref('')

async function filterVideos(): Promise<void> {
  videosLoading.value = true
  videosFailed.value = false
  try {
    videos.value = await helpApi.videos(videoFilter.value.trim() || undefined)
  } catch {
    videosFailed.value = true
  } finally {
    videosLoading.value = false
  }
}
</script>

<template>
  <AdminPage :desc="$t('admin.system.help.desc')" :title="$t('admin.system.help.title')">
    <template #actions>
      <el-button :icon="Refresh" :loading="topicsLoading" @click="loadAll">
        {{ $t('admin.common.refresh') }}
      </el-button>
    </template>

    <el-tabs v-model="activeTab">
      <!-- 帮助主题 -->
      <el-tab-pane :label="$t('admin.system.help.tabTopics')" name="topics">
        <AdminListShell
          :failed="topicsFailed"
          :loading="topicsLoading"
          :page="1"
          :page-size="topics.length || 1"
          :paginate="false"
          :rows="topics"
          :selectable="false"
          :total="topics.length"
          @refresh="loadAll"
        >
          <template #actions>
            <el-button
              v-auth="'module_system:setting:edit'"
              :icon="Plus"
              type="primary"
              @click="openCreate"
            >
              {{ $t('admin.system.help.createTopic') }}
            </el-button>
          </template>

          <el-table-column :label="$t('admin.system.help.colPageKey')" min-width="160"
                           prop="page_key"/>
          <el-table-column :label="$t('admin.system.help.colTitle')" min-width="180" prop="title"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.help.colTags')" min-width="200">
            <template #default="{ row }">
              <el-tag v-for="tag in (row as HelpTopicSummary).tags" :key="tag" class="topic-tag"
                      size="small">
                {{ tag }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.system.help.colLanguage')" align="center" prop="language"
                           width="110"/>
          <el-table-column :label="$t('admin.system.help.colSource')" align="center" width="110">
            <template #default="{ row }">
              <el-tag :type="(row as HelpTopicSummary).is_default ? 'info' : 'success'" size="small">
                {{
                  (row as HelpTopicSummary).is_default
                    ? $t('admin.system.help.builtin')
                    : $t('admin.system.help.custom')
                }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.common.actions')" fixed="right" width="220">
            <template #default="{ row }">
              <el-button link type="primary" @click="openView(row as HelpTopicSummary)">
                {{ $t('admin.system.help.view') }}
              </el-button>
              <el-button
                v-auth="'module_system:setting:edit'"
                link
                type="primary"
                @click="openEdit(row as HelpTopicSummary)"
              >
                {{ $t('admin.system.help.edit') }}
              </el-button>
              <el-button
                v-auth="'module_system:setting:edit'"
                :icon="Delete"
                link
                type="danger"
                @click="removeTopic(row as HelpTopicSummary)"
              >
                {{ $t('admin.common.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </AdminListShell>
      </el-tab-pane>

      <!-- 搜索与字段提示 -->
      <el-tab-pane :label="$t('admin.system.help.tabTools')" name="tools">
        <section class="mcard mb-3">
          <div class="mcard__head">
            <span class="mcard__title">{{ $t('admin.system.help.searchSection') }}</span>
          </div>
          <p class="hint mb-2">{{ $t('admin.system.help.searchHint') }}</p>
          <div class="row-inline">
            <el-input
              v-model="searchForm.q"
              :placeholder="$t('admin.system.help.searchPlaceholder')"
              clearable
              style="max-width: 320px"
              @keyup.enter="runSearch"
            />
            <el-input-number v-model="searchForm.limit" :max="100" :min="1" style="width: 140px"/>
            <el-button :icon="Search" :loading="searchLoading" type="primary" @click="runSearch">
              {{ $t('admin.system.help.searchButton') }}
            </el-button>
          </div>

          <el-table v-if="searchResults.length" :data="searchResults" border class="mt-3" size="small">
            <el-table-column :label="$t('admin.system.help.colTitle')" min-width="160" prop="title"/>
            <el-table-column :label="$t('admin.system.help.colPageKey')" min-width="140"
                             prop="page_key"/>
            <el-table-column :label="$t('admin.system.help.colScore')" align="right" prop="score"
                             width="100"/>
            <el-table-column :label="$t('admin.system.help.colMatched')" min-width="140">
              <template #default="{ row }">
                <el-tag v-for="field in (row as HelpSearchItem).matched_fields" :key="field"
                        class="topic-tag" size="small">
                  {{ field }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.system.help.colExcerpt')" min-width="260" prop="excerpt"
                             show-overflow-tooltip/>
          </el-table>
          <el-empty v-else-if="searchDone" :description="$t('admin.system.help.searchEmpty')"
                    :image-size="60"/>
        </section>

        <section class="mcard">
          <div class="mcard__head">
            <span class="mcard__title">{{ $t('admin.system.help.tooltipSection') }}</span>
          </div>
          <p class="hint mb-2">{{ $t('admin.system.help.tooltipHint') }}</p>
          <div class="row-inline">
            <el-input
              v-model="tooltipForm.field"
              :placeholder="$t('admin.system.help.tooltipFieldPlaceholder')"
              clearable
              style="max-width: 220px"
              @keyup.enter="runTooltip"
            />
            <el-input
              v-model="tooltipForm.context"
              :placeholder="$t('admin.system.help.tooltipContextPlaceholder')"
              clearable
              style="max-width: 200px"
              @keyup.enter="runTooltip"
            />
            <el-button :loading="tooltipLoading" type="primary" @click="runTooltip">
              {{ $t('admin.system.help.tooltipButton') }}
            </el-button>
          </div>

          <el-alert
            v-if="tooltipResult"
            :closable="false"
            :title="tooltipResult.tooltip ?? $t('admin.system.help.tooltipNotFound')"
            :type="tooltipResult.tooltip ? 'success' : 'info'"
            class="mt-3"
            show-icon
          />
        </section>
      </el-tab-pane>

      <!-- 视频教程 -->
      <el-tab-pane :label="$t('admin.system.help.tabVideos')" name="videos">
        <p class="hint mb-2">{{ $t('admin.system.help.videosHint') }}</p>
        <div class="row-inline mb-3">
          <el-input
            v-model="videoFilter"
            :placeholder="$t('admin.system.help.videoFilterPlaceholder')"
            clearable
            style="max-width: 260px"
            @keyup.enter="filterVideos"
          />
          <el-button :loading="videosLoading" type="primary" @click="filterVideos">
            {{ $t('admin.system.help.videoFilterButton') }}
          </el-button>
        </div>

        <el-alert
          v-if="videosFailed"
          :closable="false"
          :title="$t('admin.common.loadFailed')"
          class="mb-3"
          show-icon
          type="error"
        />

        <el-table v-if="videos.length" :data="videos" border size="small" stripe>
          <el-table-column :label="$t('admin.system.help.colVideoTitle')" min-width="180"
                           prop="title"/>
          <el-table-column :label="$t('admin.system.help.colVideoDesc')" min-width="240"
                           prop="description" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.help.colDuration')" align="center" prop="duration"
                           width="100"/>
          <el-table-column :label="$t('admin.system.help.colVideoTopic')" min-width="140"
                           prop="topic"/>
          <el-table-column :label="$t('admin.system.help.colUrl')" min-width="200">
            <template #default="{ row }">
              <a :href="(row as HelpVideoItem).url" rel="noopener" target="_blank">
                {{ (row as HelpVideoItem).url }}
              </a>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else :description="$t('admin.system.help.videosEmpty')" :image-size="60"/>
      </el-tab-pane>
    </el-tabs>

    <!-- 主题详情（只读） -->
    <el-drawer v-model="detailVisible" :title="detailTopic?.title" size="480px">
      <div v-loading="detailLoading">
        <template v-if="detailTopic">
          <div class="detail-row">
            <span class="detail-label">{{ $t('admin.system.help.colPageKey') }}</span>
            <span class="detail-value">{{ detailTopic.page_key }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">{{ $t('admin.system.help.colLanguage') }}</span>
            <span class="detail-value">{{ detailTopic.language }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">{{ $t('admin.system.help.detailTags') }}</span>
            <span class="detail-value">
              <el-tag v-for="tag in detailTopic.tags" :key="tag" class="topic-tag" size="small">
                {{ tag }}
              </el-tag>
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-label">{{ $t('admin.system.help.detailLinks') }}</span>
            <span class="detail-value">
              <template v-if="detailTopic.related_links?.length">
                <div v-for="link in detailTopic.related_links" :key="link.url">
                  <a :href="link.url" rel="noopener" target="_blank">{{ link.title }}</a>
                </div>
              </template>
              <span v-else>{{ $t('admin.system.help.detailNoLinks') }}</span>
            </span>
          </div>
          <el-divider/>
          <p class="hint mb-2">{{ $t('admin.system.help.detailContent') }}</p>
          <!-- 帮助内容按契约即为 HTML -->
          <div class="help-content" v-html="detailTopic.content"/>
        </template>
      </div>
    </el-drawer>

    <!-- 新建 / 覆盖 -->
    <AdminFormDrawer
      v-model="formDrawerVisible"
      :loading="formSaving"
      :title="formDrawerTitle"
      @confirm="submitTopic"
    >
      <el-form :model="topicForm" label-width="120px">
        <el-form-item :label="$t('admin.system.help.formPageKey')" required>
          <el-input v-model="topicForm.page_key" :disabled="formMode === 'edit'"/>
          <p class="hint">{{ $t('admin.system.help.pageKeyHint') }}</p>
        </el-form-item>
        <el-form-item :label="$t('admin.system.help.formTitle')" required>
          <el-input v-model="topicForm.title"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.help.formContent')" required>
          <el-input v-model="topicForm.content" :autosize="{minRows: 6, maxRows: 16}" type="textarea"/>
          <p class="hint">{{ $t('admin.system.help.contentHint') }}</p>
        </el-form-item>
        <el-form-item :label="$t('admin.system.help.formTags')">
          <el-input v-model="topicForm.tagsText"
                    :placeholder="$t('admin.system.help.tagsHint')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.help.formLanguage')">
          <el-select v-model="topicForm.language" style="width: 100%">
            <el-option label="zh_CN" value="zh_CN"/>
            <el-option label="en_US" value="en_US"/>
          </el-select>
          <p class="hint">{{ $t('admin.system.help.languageHint') }}</p>
        </el-form-item>
        <el-form-item :label="$t('admin.system.help.formRelatedLinks')">
          <el-input v-model="topicForm.relatedLinksText" :autosize="{minRows: 2, maxRows: 8}"
                    type="textarea"/>
          <p class="hint">{{ $t('admin.system.help.relatedLinksHint') }}</p>
        </el-form-item>
      </el-form>
    </AdminFormDrawer>
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

.hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.row-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.topic-tag {
  margin: 0 4px 4px 0;
}

.detail-row {
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
}

.detail-label {
  flex: 0 0 72px;
  color: var(--color-fg-subtle, #909399);
}

.detail-value {
  flex: 1 1 auto;
  word-break: break-all;
}

.help-content {
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
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
