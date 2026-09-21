<script lang="ts" setup>
/**
 * 多平台发布（third-party-publish 底座）
 *
 * 两个 tab：
 *  - **渠道配置**：`/content/third-party-publish/channel`
 *    凭据加密存储、**永不回传**（列表只显示"已配置/未配置"）；`adapter_ready` 标注该平台的
 *    适配器是否已接入。
 *  - **发布任务**：`/content/third-party-publish/task`
 *    创建后后端**立即尝试执行**；失败如实显示原因（例如"未实现该平台的发布适配器"），
 *    可用「重试」按钮再次执行（复用创建时冻结的载荷快照）。
 *
 * 平台适配器按清单分期接入：`platforms()` 返回**已接入**的平台，为空时页面顶部如实提示，
 * 不伪造任何"可用平台"。
 */
import {Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {
  articleApi,
  type ArticleItem,
  type PublishChannelItem,
  type PublishChannelQuery,
  type PublishLogItem,
  type PublishPlatform,
  type PublishTaskItem,
  type PublishTaskQuery,
  thirdPartyPublishApi,
} from '@/api'
import {useTable} from '@/hooks/useTable'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.thirdPartyPublish.title',
  permission: 'module_content:third_party_publish:view',
})

const {t} = useI18n()
const activeTab = ref('channel')

// ---- 已接入的平台适配器 ----
const platforms = ref<PublishPlatform[]>([])
const platformsLoaded = ref(false)

async function loadPlatforms(): Promise<void> {
  try {
    const data = await thirdPartyPublishApi.platforms()
    platforms.value = data.items ?? []
  } finally {
    platformsLoaded.value = true
  }
}

void loadPlatforms()

// ---------------------------------------------------------------- 渠道
const channelTable = useTable<PublishChannelItem, PublishChannelQuery>({
  fetcher: (params) => thirdPartyPublishApi.listChannels(params),
  defaultQuery: {keyword: '', platform: '', is_active: undefined},
  syncUrl: true,
})

const channelFormVisible = ref(false)
const editingChannelId = ref<number | null>(null)
const savingChannel = ref(false)
const verifyingId = ref<number | null>(null)
const channelForm = reactive({
  name: '',
  platform: '',
  endpoint: '',
  credentialsText: '',
  is_active: true,
})

const channelFormTitle = computed(() =>
  editingChannelId.value
    ? t('admin.content.thirdPartyPublish.channel.editTitle')
    : t('admin.content.thirdPartyPublish.channel.createTitle'),
)

function openChannelCreate(): void {
  editingChannelId.value = null
  Object.assign(channelForm, {
    name: '',
    platform: '',
    endpoint: '',
    credentialsText: '',
    is_active: true,
  })
  channelFormVisible.value = true
}

function openChannelEdit(row: PublishChannelItem): void {
  editingChannelId.value = row.id
  Object.assign(channelForm, {
    name: row.name,
    platform: row.platform,
    endpoint: row.endpoint || '',
    // 凭据永不回传：编辑时留空表示保持原值
    credentialsText: '',
    is_active: row.is_active,
  })
  channelFormVisible.value = true
}

/** 把表单里的凭据文本解析成对象；空文本返回 undefined（= 保持原值） */
function parseCredentials(): Record<string, unknown> | undefined {
  const raw = channelForm.credentialsText.trim()
  if (!raw) return undefined
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    ElMessage.warning(t('admin.content.thirdPartyPublish.channel.credentialsInvalid'))
    return undefined
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    ElMessage.warning(t('admin.content.thirdPartyPublish.channel.credentialsInvalid'))
    return undefined
  }
  return parsed as Record<string, unknown>
}

async function submitChannel(): Promise<void> {
  if (!channelForm.name.trim()) {
    ElMessage.warning(t('admin.content.thirdPartyPublish.channel.nameRequired'))
    return
  }
  if (!editingChannelId.value && !channelForm.platform.trim()) {
    ElMessage.warning(t('admin.content.thirdPartyPublish.channel.platformRequired'))
    return
  }
  const credentials = parseCredentials()
  if (channelForm.credentialsText.trim() && credentials === undefined) return
  savingChannel.value = true
  try {
    if (editingChannelId.value) {
      await thirdPartyPublishApi.updateChannel(editingChannelId.value, {
        name: channelForm.name.trim(),
        endpoint: channelForm.endpoint.trim() || null,
        credentials,
        is_active: channelForm.is_active,
      })
    } else {
      await thirdPartyPublishApi.createChannel({
        name: channelForm.name.trim(),
        platform: channelForm.platform.trim(),
        endpoint: channelForm.endpoint.trim() || null,
        credentials: credentials ?? {},
        is_active: channelForm.is_active,
      })
    }
    ElMessage.success(t('admin.common.save'))
    channelFormVisible.value = false
    await channelTable.load()
  } finally {
    savingChannel.value = false
  }
}

async function verifyChannel(row: PublishChannelItem): Promise<void> {
  verifyingId.value = row.id
  try {
    const result = await thirdPartyPublishApi.verifyChannel(row.id)
    if (result.success) {
      ElMessage.success(result.message || t('admin.content.thirdPartyPublish.channel.verifyOk'))
    } else {
      ElMessage.warning(result.message || t('admin.content.thirdPartyPublish.channel.verifyFailed'))
    }
  } finally {
    verifyingId.value = null
  }
}

async function removeChannel(row: PublishChannelItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.content.thirdPartyPublish.channel.deleteConfirm', {name: row.name}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await thirdPartyPublishApi.removeChannel(row.id)
  ElMessage.success(t('admin.common.delete'))
  await channelTable.load()
}

// ---------------------------------------------------------------- 发布任务
const taskTable = useTable<PublishTaskItem, PublishTaskQuery>({
  fetcher: (params) => thirdPartyPublishApi.listTasks(params),
  defaultQuery: {status: ''},
  syncUrl: true,
})

const taskFormVisible = ref(false)
const creatingTask = ref(false)
const retryingId = ref<number | null>(null)
const taskForm = reactive<{ article_id: number | null; channel_id: number | null }>({
  article_id: null,
  channel_id: null,
})

const articleOptions = ref<ArticleItem[]>([])
const articleLoading = ref(false)

async function searchArticles(keyword: string): Promise<void> {
  articleLoading.value = true
  try {
    const result = await articleApi.list({keyword: keyword || undefined, page: 1, page_size: 20})
    articleOptions.value = result.items
  } finally {
    articleLoading.value = false
  }
}

function openTaskCreate(): void {
  taskForm.article_id = null
  taskForm.channel_id = null
  articleOptions.value = []
  void searchArticles('')
  taskFormVisible.value = true
}

async function submitTask(): Promise<void> {
  if (!taskForm.article_id || !taskForm.channel_id) {
    ElMessage.warning(t('admin.content.thirdPartyPublish.task.formRequired'))
    return
  }
  creatingTask.value = true
  try {
    const detail = await thirdPartyPublishApi.createTask({
      article_id: taskForm.article_id,
      channel_id: taskForm.channel_id,
    })
    // 创建即执行：如实反馈结果（失败时给出后端写明的 last_error）
    if (detail.status === 'success') {
      ElMessage.success(t('admin.content.thirdPartyPublish.task.createdOk'))
    } else {
      ElMessage.warning(
        detail.last_error || t('admin.content.thirdPartyPublish.task.createdFailed'),
      )
    }
    taskFormVisible.value = false
    await taskTable.load()
  } finally {
    creatingTask.value = false
  }
}

async function retryTask(row: PublishTaskItem): Promise<void> {
  retryingId.value = row.id
  try {
    const detail = await thirdPartyPublishApi.retryTask(row.id)
    if (detail.status === 'success') {
      ElMessage.success(t('admin.content.thirdPartyPublish.task.retryOk'))
    } else {
      ElMessage.warning(
        detail.last_error || t('admin.content.thirdPartyPublish.task.retryFailed'),
      )
    }
    await taskTable.load()
  } finally {
    retryingId.value = null
  }
}

async function removeTask(row: PublishTaskItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.content.thirdPartyPublish.task.deleteConfirm', {id: row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await thirdPartyPublishApi.removeTask(row.id)
  ElMessage.success(t('admin.common.delete'))
  await taskTable.load()
}

// ---- 任务详情 / 日志 ----
const detailVisible = ref(false)
const detailTask = ref<PublishTaskItem | null>(null)
const detailLogs = ref<PublishLogItem[]>([])
const detailLoading = ref(false)

async function openDetail(row: PublishTaskItem): Promise<void> {
  detailVisible.value = true
  detailLoading.value = true
  detailTask.value = row
  detailLogs.value = []
  try {
    const detail = await thirdPartyPublishApi.getTask(row.id)
    detailTask.value = detail
    detailLogs.value = detail.logs ?? []
  } finally {
    detailLoading.value = false
  }
}

function statusTagType(status: string): 'success' | 'danger' | 'warning' | 'info' {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'publishing') return 'warning'
  return 'info'
}
</script>

<template>
  <div class="page-container">
    <!-- 平台适配器未接入时的如实提示 -->
    <el-alert
      v-if="platformsLoaded && !platforms.length"
      :closable="false"
      :title="$t('admin.content.thirdPartyPublish.noPlatforms')"
      class="adapter-alert"
      show-icon
      type="warning"
    />

    <el-tabs v-model="activeTab" type="border-card">
      <!-- ---------------------------------------------------- 渠道配置 -->
      <el-tab-pane :label="$t('admin.content.thirdPartyPublish.tabChannels')" name="channel">
        <el-form :inline="true" :model="channelTable.query" @submit.prevent="channelTable.search()">
          <el-form-item :label="$t('admin.content.thirdPartyPublish.keyword')">
            <el-input
              v-model="channelTable.query.keyword"
              :placeholder="$t('admin.content.thirdPartyPublish.channel.keywordPlaceholder')"
              clearable
              style="width: 200px"
              @keyup.enter="channelTable.search()"
            />
          </el-form-item>
          <el-form-item :label="$t('admin.content.thirdPartyPublish.channel.platform')">
            <el-input
              v-model="channelTable.query.platform"
              :placeholder="$t('admin.content.thirdPartyPublish.channel.platformPlaceholder')"
              clearable
              style="width: 170px"
            />
          </el-form-item>
          <el-form-item :label="$t('admin.common.status')">
            <el-select
              v-model="channelTable.query.is_active"
              :placeholder="$t('admin.common.all')"
              clearable
              style="width: 120px"
            >
              <el-option :label="$t('admin.common.enabled')" :value="true"/>
              <el-option :label="$t('admin.common.disabled')" :value="false"/>
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button :icon="Search" type="primary" @click="channelTable.search()">
              {{ $t('admin.common.search') }}
            </el-button>
            <el-button :icon="Refresh" @click="channelTable.reset()">
              {{ $t('admin.common.reset') }}
            </el-button>
          </el-form-item>
        </el-form>

        <div class="table-toolbar">
          <el-button
            v-auth="'module_content:third_party_publish:create'"
            :icon="Plus"
            type="primary"
            @click="openChannelCreate"
          >
            {{ $t('admin.content.thirdPartyPublish.channel.createTitle') }}
          </el-button>
          <span class="table-toolbar__total">
            {{ $t('admin.common.totalItems', {n: channelTable.total.value}) }}
          </span>
        </div>

        <AdminTableSkeleton v-if="channelTable.loading.value && !channelTable.list.value.length" :rows="5"/>
        <AdminEmpty
          v-else-if="!channelTable.loading.value && !channelTable.list.value.length"
          :desc="$t('admin.content.thirdPartyPublish.emptyDesc')"
          :title="$t('admin.content.thirdPartyPublish.emptyTitle')"
        />

        <el-table v-else v-loading="channelTable.loading.value" :data="channelTable.list.value" border stripe>
          <el-table-column :label="$t('admin.common.name')" min-width="140" prop="name" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.content.thirdPartyPublish.channel.platform')" min-width="170">
            <template #default="{ row }">
              <span>{{ (row as PublishChannelItem).platform }}</span>
              <el-tag
                :type="(row as PublishChannelItem).adapter_ready ? 'success' : 'warning'"
                class="adapter-tag"
                size="small"
              >
                {{
                  (row as PublishChannelItem).adapter_ready
                    ? $t('admin.content.thirdPartyPublish.channel.adapterReady')
                    : $t('admin.content.thirdPartyPublish.channel.adapterMissing')
                }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.content.thirdPartyPublish.channel.endpoint')" min-width="180"
                           prop="endpoint" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.content.thirdPartyPublish.channel.credentials')" width="120">
            <template #default="{ row }">
              <el-tag :type="(row as PublishChannelItem).has_credentials ? 'info' : 'danger'" size="small">
                {{
                  (row as PublishChannelItem).has_credentials
                    ? $t('admin.content.thirdPartyPublish.channel.hasCredentials')
                    : $t('admin.content.thirdPartyPublish.channel.noCredentials')
                }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.common.status')" width="90">
            <template #default="{ row }">
              <el-tag :type="(row as PublishChannelItem).is_active ? 'success' : 'info'" size="small">
                {{
                  (row as PublishChannelItem).is_active
                    ? $t('admin.common.enabled')
                    : $t('admin.common.disabled')
                }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.common.actions')" fixed="right" width="220">
            <template #default="{ row }">
              <el-button
                v-auth="'module_content:third_party_publish:edit'"
                :loading="verifyingId === (row as PublishChannelItem).id"
                link
                type="primary"
                @click="verifyChannel(row as PublishChannelItem)"
              >
                {{ $t('admin.content.thirdPartyPublish.channel.verify') }}
              </el-button>
              <el-button
                v-auth="'module_content:third_party_publish:edit'"
                link
                type="primary"
                @click="openChannelEdit(row as PublishChannelItem)"
              >
                {{ $t('admin.common.edit') }}
              </el-button>
              <el-button
                v-auth="'module_content:third_party_publish:delete'"
                link
                type="danger"
                @click="removeChannel(row as PublishChannelItem)"
              >
                {{ $t('admin.common.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          :current-page="channelTable.page.value"
          :page-size="channelTable.pageSize.value"
          :page-sizes="[10, 20, 50, 100]"
          :total="channelTable.total.value"
          background
          class="table-pagination"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="channelTable.onPageChange"
          @size-change="channelTable.onSizeChange"
        />
      </el-tab-pane>

      <!-- ---------------------------------------------------- 发布任务 -->
      <el-tab-pane :label="$t('admin.content.thirdPartyPublish.tabTasks')" name="task">
        <el-form :inline="true" :model="taskTable.query" @submit.prevent="taskTable.search()">
          <el-form-item :label="$t('admin.content.thirdPartyPublish.task.status')">
            <el-select
              v-model="taskTable.query.status"
              :placeholder="$t('admin.common.all')"
              clearable
              style="width: 140px"
            >
              <el-option :label="$t('admin.content.thirdPartyPublish.status.pending')" value="pending"/>
              <el-option :label="$t('admin.content.thirdPartyPublish.status.publishing')" value="publishing"/>
              <el-option :label="$t('admin.content.thirdPartyPublish.status.success')" value="success"/>
              <el-option :label="$t('admin.content.thirdPartyPublish.status.failed')" value="failed"/>
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button :icon="Search" type="primary" @click="taskTable.search()">
              {{ $t('admin.common.search') }}
            </el-button>
            <el-button :icon="Refresh" @click="taskTable.reset()">{{ $t('admin.common.reset') }}</el-button>
          </el-form-item>
        </el-form>

        <div class="table-toolbar">
          <el-button
            v-auth="'module_content:third_party_publish:create'"
            :icon="Plus"
            type="primary"
            @click="openTaskCreate"
          >
            {{ $t('admin.content.thirdPartyPublish.task.createTitle') }}
          </el-button>
          <span class="table-toolbar__total">
            {{ $t('admin.common.totalItems', {n: taskTable.total.value}) }}
          </span>
        </div>

        <el-table v-loading="taskTable.loading.value" :data="taskTable.list.value" border stripe>
          <el-table-column :label="$t('admin.content.thirdPartyPublish.task.article')" min-width="200">
            <template #default="{ row }">
              <span>{{ (row as PublishTaskItem).article_title || `#${(row as PublishTaskItem).article_id}` }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.content.thirdPartyPublish.task.channel')" min-width="170">
            <template #default="{ row }">
              <span>{{ (row as PublishTaskItem).channel_name || `#${(row as PublishTaskItem).channel_id}` }}</span>
              <span v-if="(row as PublishTaskItem).channel_platform" class="channel-platform">
                {{ (row as PublishTaskItem).channel_platform }}
              </span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.content.thirdPartyPublish.task.status')" width="110">
            <template #default="{ row }">
              <el-tag :type="statusTagType((row as PublishTaskItem).status)" size="small">
                {{ $t(`admin.content.thirdPartyPublish.status.${(row as PublishTaskItem).status}`) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.content.thirdPartyPublish.task.attempts')" prop="attempts"
                           width="90"/>
          <el-table-column :label="$t('admin.content.thirdPartyPublish.task.lastError')" min-width="220"
                           show-overflow-tooltip>
            <template #default="{ row }">
              <span :class="{'task-error': (row as PublishTaskItem).last_error}">
                {{ (row as PublishTaskItem).last_error || '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.content.thirdPartyPublish.task.updatedAt')" width="170">
            <template #default="{ row }">
              {{ formatDateTime((row as PublishTaskItem).updated_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.common.actions')" fixed="right" width="220">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDetail(row as PublishTaskItem)">
                {{ $t('admin.content.thirdPartyPublish.task.detail') }}
              </el-button>
              <el-button
                v-auth="'module_content:third_party_publish:execute'"
                :loading="retryingId === (row as PublishTaskItem).id"
                link
                type="primary"
                @click="retryTask(row as PublishTaskItem)"
              >
                {{ $t('admin.content.thirdPartyPublish.task.retry') }}
              </el-button>
              <el-button
                v-auth="'module_content:third_party_publish:delete'"
                link
                type="danger"
                @click="removeTask(row as PublishTaskItem)"
              >
                {{ $t('admin.common.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          :current-page="taskTable.page.value"
          :page-size="taskTable.pageSize.value"
          :page-sizes="[10, 20, 50, 100]"
          :total="taskTable.total.value"
          background
          class="table-pagination"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="taskTable.onPageChange"
          @size-change="taskTable.onSizeChange"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- 渠道新建 / 编辑 -->
    <el-drawer v-model="channelFormVisible" :title="channelFormTitle" destroy-on-close size="480px">
      <el-form :model="channelForm" label-width="110px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input
            v-model="channelForm.name"
            :placeholder="$t('admin.content.thirdPartyPublish.channel.namePlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.content.thirdPartyPublish.channel.platform')" required>
          <el-input
            v-model="channelForm.platform"
            :disabled="!!editingChannelId"
            :placeholder="$t('admin.content.thirdPartyPublish.channel.platformPlaceholder')"
          />
          <div v-if="platforms.length" class="form-hint">
            {{
              $t('admin.content.thirdPartyPublish.channel.platformHint', {list: platforms.map((item) => item.platform).join(', ')})
            }}
          </div>
          <div v-else class="form-hint">
            {{ $t('admin.content.thirdPartyPublish.noPlatforms') }}
          </div>
        </el-form-item>
        <el-form-item :label="$t('admin.content.thirdPartyPublish.channel.endpoint')">
          <el-input
            v-model="channelForm.endpoint"
            :placeholder="$t('admin.content.thirdPartyPublish.channel.endpointPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.content.thirdPartyPublish.channel.credentials')">
          <el-input
            v-model="channelForm.credentialsText"
            :autosize="{minRows: 4, maxRows: 10}"
            :placeholder="$t('admin.content.thirdPartyPublish.channel.credentialsPlaceholder')"
            type="textarea"
          />
          <div class="form-hint">{{ $t('admin.content.thirdPartyPublish.channel.credentialsKeep') }}</div>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="channelForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="channelFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="savingChannel" type="primary" @click="submitChannel">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-drawer>

    <!-- 新建发布任务 -->
    <el-dialog v-model="taskFormVisible" :title="$t('admin.content.thirdPartyPublish.task.createTitle')"
               width="520px">
      <el-form :model="taskForm" label-width="90px">
        <el-form-item :label="$t('admin.content.thirdPartyPublish.task.article')" required>
          <el-select
            v-model="taskForm.article_id"
            :loading="articleLoading"
            :placeholder="$t('admin.content.thirdPartyPublish.task.articlePlaceholder')"
            :remote-method="searchArticles"
            filterable
            remote
            reserve-keyword
            style="width: 100%"
          >
            <el-option
              v-for="item in articleOptions"
              :key="item.id"
              :label="item.title"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.content.thirdPartyPublish.task.channel')" required>
          <el-select
            v-model="taskForm.channel_id"
            :placeholder="$t('admin.content.thirdPartyPublish.task.channelPlaceholder')"
            style="width: 100%"
          >
            <el-option
              v-for="item in channelTable.list.value"
              :key="item.id"
              :label="`${item.name}（${item.platform}）`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="taskFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="creatingTask" type="primary" @click="submitTask">
          {{ $t('admin.content.thirdPartyPublish.task.createAndRun') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 任务详情 + 尝试记录 -->
    <el-drawer v-model="detailVisible" :title="$t('admin.content.thirdPartyPublish.task.detailTitle')"
               destroy-on-close size="560px">
      <div v-loading="detailLoading">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item :label="$t('admin.content.thirdPartyPublish.task.article')">
            {{ detailTask?.article_title || detailTask?.article_id }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.content.thirdPartyPublish.task.channel')">
            {{ detailTask?.channel_name || detailTask?.channel_id }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.content.thirdPartyPublish.task.status')">
            {{ detailTask?.status }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.content.thirdPartyPublish.task.attempts')">
            {{ detailTask?.attempts }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.content.thirdPartyPublish.task.externalUrl')">
            <a v-if="detailTask?.external_url" :href="detailTask.external_url" rel="noopener" target="_blank">
              {{ detailTask.external_url }}
            </a>
            <span v-else>—</span>
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.content.thirdPartyPublish.task.lastError')">
            {{ detailTask?.last_error || '—' }}
          </el-descriptions-item>
        </el-descriptions>

        <h4 class="detail-title">{{ $t('admin.content.thirdPartyPublish.task.logs') }}</h4>
        <el-table :data="detailLogs" border size="small">
          <el-table-column :label="$t('admin.content.thirdPartyPublish.task.status')" width="90">
            <template #default="{ row }">
              <el-tag :type="statusTagType((row as PublishLogItem).status)" size="small">
                {{ (row as PublishLogItem).status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.content.thirdPartyPublish.task.logMessage')" min-width="220"
                           prop="message" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.content.thirdPartyPublish.task.logDuration')" width="110">
            <template #default="{ row }">
              {{ (row as PublishLogItem).duration_ms ?? '—' }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.content.thirdPartyPublish.task.updatedAt')" width="170">
            <template #default="{ row }">
              {{ formatDateTime((row as PublishLogItem).created_at) }}
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.adapter-alert {
  margin-bottom: 12px;
}

.adapter-tag {
  margin-left: 6px;
}

.channel-platform {
  margin-left: 6px;
  color: var(--el-text-color-secondary);
}

.task-error {
  color: var(--el-color-danger);
}

.form-hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.detail-title {
  margin: 18px 0 8px;
  font-size: 14px;
  font-weight: 600;
}
</style>
