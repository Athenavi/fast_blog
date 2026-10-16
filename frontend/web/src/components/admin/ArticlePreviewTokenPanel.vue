<script lang="ts" setup>
/**
 * 草稿预览令牌面板（文章编辑页右栏）
 *
 * 从 `pages/content/article/[id].vue` 抽出来：它管的是"给未发布的草稿签发一个可对外
 * 分享的临时链接"这一整件事（生成 / 复制 / 撤销 / 清理），只依赖一个 `articleId`，
 * 与页面主体没有耦合，也不向页面回传任何东西。
 *
 * ## 补上的三态区分
 *
 * 抽取前列表只有 `v-if="!previewTokens.length"` 两个分支：请求**还没回来**和
 * 请求**失败**时，previewTokens 都是空数组，于是都渲染成"暂无令牌"。实际上令牌
 * 是否签发过关系到文章能不能被外部预览，把"读取失败"伪装成"一个都没有"是有害的。
 * 现在显式区分：加载中（且尚无数据）/ 加载失败可重试 / 确实为空。
 */
import {computed, onMounted, reactive, ref, watch} from 'vue'

import {articleApi, type ArticlePreviewToken, type ArticlePreviewTokenCreatePayload,} from '@/api'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {formatDateTime} from '@/utils/format'

const props = defineProps<{
  /** 当前文章 id；新建（尚未保存）时为 null，此时不能签发令牌 */
  articleId: number | null
}>()

const {t} = useI18n()

/** 该文章已签发的预览令牌（GET /content/article/{id}/preview-tokens） */
const previewTokens = ref<ArticlePreviewToken[]>([])
const previewTokensLoading = ref(false)
/** 读取令牌列表失败：与"一个都没有"区分开 */
const loadFailed = ref(false)

/** 生成令牌入参：有效期 / 可选口令 / 可选访问上限 */
const tokenForm = reactive<ArticlePreviewTokenCreatePayload>({
  expires_hours: 24,
  password: '',
  max_views: undefined,
})
const tokenCreating = ref(false)
/** 最近一次生成的令牌：明文只在生成响应里出现，提示用户立即复制 */
const latestToken = ref<ArticlePreviewToken | null>(null)

/** 令牌对应的公开预览地址（前台页面 `/articles/preview/{token}`，无须登录） */
function tokenPreviewUrl(value: string): string {
  const origin = import.meta.client ? window.location.origin : ''
  return `${origin}/articles/preview/${value}`
}

/** 最近生成的令牌预览地址（模板里避免直接解引用可空 ref） */
const latestTokenUrl = computed(() =>
  latestToken.value ? tokenPreviewUrl(latestToken.value.token) : '',
)

async function loadPreviewTokens(): Promise<void> {
  const id = props.articleId
  if (id === null) {
    previewTokens.value = []
    return
  }
  previewTokensLoading.value = true
  loadFailed.value = false
  try {
    previewTokens.value = await articleApi.listPreviewTokens(id)
  } catch {
    previewTokens.value = []
    loadFailed.value = true
  } finally {
    previewTokensLoading.value = false
  }
}

async function copyText(text: string): Promise<void> {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(t('admin.content.article.previewToken.copied'))
  } catch {
    // 剪贴板不可用（非安全上下文/无权限）时退化为把链接显示出来让用户手抄
    ElMessage.warning(text)
  }
}

function copyTokenLink(value: string): void {
  void copyText(tokenPreviewUrl(value))
}

async function createPreviewToken(): Promise<void> {
  const id = props.articleId
  if (id === null) {
    ElMessage.warning(t('admin.content.article.saveBeforePreview'))
    return
  }
  tokenCreating.value = true
  try {
    const payload: ArticlePreviewTokenCreatePayload = {expires_hours: tokenForm.expires_hours ?? 24}
    if (tokenForm.password) payload.password = tokenForm.password
    if (tokenForm.max_views) payload.max_views = tokenForm.max_views
    latestToken.value = await articleApi.createPreviewToken(id, payload)
    // 口令与访问上限不留在表单里：它们只对刚签发的这一个令牌有意义
    tokenForm.password = ''
    tokenForm.max_views = undefined
    ElMessage.success(t('admin.content.article.previewToken.created'))
    await loadPreviewTokens()
  } catch {
    /* 失败提示由 http 拦截器统一给出 */
  } finally {
    tokenCreating.value = false
  }
}

async function revokeToken(row: ArticlePreviewToken): Promise<void> {
  try {
    await ElMessageBox.confirm(
      t('admin.content.article.previewToken.revokeConfirm'),
      t('admin.common.notice'),
      {type: 'warning'},
    )
  } catch {
    return
  }
  try {
    await articleApi.revokePreviewToken(row.id)
    if (latestToken.value?.id === row.id) latestToken.value = null
    ElMessage.success(t('admin.content.article.previewToken.revoked'))
    await loadPreviewTokens()
  } catch {
    /* 失败提示由 http 拦截器统一给出 */
  }
}

async function cleanupTokens(): Promise<void> {
  try {
    const result = await articleApi.cleanupPreviewTokens()
    ElMessage.success(t('admin.content.article.previewToken.cleanupDone', {n: result.removed}))
    await loadPreviewTokens()
  } catch {
    /* 失败提示由 http 拦截器统一给出 */
  }
}

onMounted(() => void loadPreviewTokens())

// 保存后拿到文章 id（新建 → 编辑）时补上列表
watch(
  () => props.articleId,
  (id) => {
    if (id !== null) void loadPreviewTokens()
  },
)
</script>

<template>
  <el-card shadow="never">
    <template #header>{{ $t('admin.content.article.previewToken.title') }}</template>

    <p class="assist-hint">{{ $t('admin.content.article.previewToken.desc') }}</p>

    <el-form label-position="top">
      <el-form-item :label="$t('admin.content.article.previewToken.expiresHours')">
        <el-input-number v-model="tokenForm.expires_hours" :max="720" :min="1" style="width: 100%"/>
      </el-form-item>
      <el-form-item :label="$t('admin.content.article.previewToken.password')">
        <el-input
          v-model="tokenForm.password"
          :placeholder="$t('admin.content.article.previewToken.passwordPlaceholder')"
          show-password
          type="password"
        />
      </el-form-item>
      <el-form-item :label="$t('admin.content.article.previewToken.maxViews')">
        <el-input-number v-model="tokenForm.max_views" :max="10000" :min="1" style="width: 100%"/>
      </el-form-item>
    </el-form>

    <el-button
      :disabled="articleId === null"
      :loading="tokenCreating"
      type="primary"
      @click="createPreviewToken"
    >
      {{ $t('admin.content.article.previewToken.create') }}
    </el-button>

    <!-- 明文只在生成响应里出现，所以生成后立刻把完整链接给出来 -->
    <div v-if="latestToken" class="token-new">
      <span class="token-new__hint">{{ $t('admin.content.article.previewToken.newTokenHint') }}</span>
      <el-input :model-value="latestTokenUrl" readonly>
        <template #append>
          <el-button @click="copyText(latestTokenUrl)">
            {{ $t('admin.content.article.previewToken.copyLink') }}
          </el-button>
        </template>
      </el-input>
    </div>

    <div class="token-list__head">
      <span>{{ $t('admin.content.article.previewToken.list') }}</span>
      <el-button link size="small" @click="cleanupTokens">
        {{ $t('admin.content.article.previewToken.cleanup') }}
      </el-button>
    </div>

    <p v-if="previewTokensLoading && !previewTokens.length" class="assist-hint">
      {{ $t('common.loading') }}
    </p>
    <div v-else-if="loadFailed" class="assist-failed">
      <span>{{ $t('admin.common.loadFailed') }}</span>
      <el-button link size="small" @click="loadPreviewTokens">{{ $t('admin.common.retry') }}</el-button>
    </div>
    <p v-else-if="!previewTokens.length" class="assist-hint">
      {{ $t('admin.content.article.previewToken.empty') }}
    </p>
    <ul v-else class="assist-list">
      <li v-for="row in previewTokens" :key="row.id" class="assist-row">
        <span class="assist-row__main">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{
              row.is_active
                ? $t('admin.content.article.previewToken.active')
                : $t('admin.content.article.previewToken.inactive')
            }}
          </el-tag>
          <el-tag v-if="row.has_password" size="small" type="warning">
            {{ $t('admin.content.article.previewToken.hasPassword') }}
          </el-tag>
          <span class="assist-row__meta">
            {{ $t('admin.content.article.previewToken.viewCount') }}
            {{ row.view_count }}/
            {{ row.max_views ?? $t('admin.content.article.previewToken.unlimited') }}
          </span>
        </span>
        <span class="assist-row__meta">
          {{ formatDateTime(row.expires_at) }}
          <el-button link size="small" @click="copyTokenLink(row.token)">
            {{ $t('admin.content.article.previewToken.copyLink') }}
          </el-button>
          <el-button v-if="row.is_active" link size="small" type="danger" @click="revokeToken(row)">
            {{ $t('admin.content.article.previewToken.revoke') }}
          </el-button>
        </span>
      </li>
    </ul>
  </el-card>
</template>

<style scoped>
.assist-hint {
  margin: 0 0 var(--admin-gap-xs);
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

/* 加载失败：与"暂无令牌"区分开，并给一个原地重试入口 */
.assist-failed {
  display: flex;
  gap: var(--admin-gap-xs);
  align-items: center;
  margin-bottom: var(--admin-gap-xs);
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

.assist-list {
  display: flex;
  flex-direction: column;
  gap: var(--admin-gap-xs);
  padding: 0;
  margin: 0;
  list-style: none;
}

.assist-row {
  display: flex;
  gap: var(--admin-gap-sm);
  align-items: center;
  justify-content: space-between;
}

.assist-row__main {
  display: flex;
  gap: var(--admin-gap-xs);
  align-items: center;
  min-width: 0;
}

.assist-row__meta {
  display: inline-flex;
  gap: var(--admin-gap-xs);
  align-items: center;
  flex-shrink: 0;
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

/* 刚生成的令牌：明文只出现一次，需要显著一些 */
.token-new {
  display: flex;
  flex-direction: column;
  gap: var(--admin-gap-xs);
  margin-top: var(--admin-gap-sm);
}

.token-new__hint {
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

.token-list__head {
  display: flex;
  gap: var(--admin-gap-sm);
  align-items: center;
  justify-content: space-between;
  margin: var(--admin-gap) 0 var(--admin-gap-xs);
  font-weight: 600;
  color: var(--admin-fg);
}
</style>
