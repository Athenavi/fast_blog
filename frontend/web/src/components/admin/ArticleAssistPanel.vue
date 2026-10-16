<script lang="ts" setup>
/**
 * 内容助手面板（文章编辑页右栏）
 *
 * 从 `pages/content/article/[id].vue` 抽出来：它自带 5 个标签页、5 个独立的加载
 * 函数与一整套列表样式，与页面主体（标题 / 正文 / 发布字段）没有耦合，只依赖一个
 * `articleId`；向外的唯一动作是"采纳某个建议标签"（由页面写进表单并标记未保存）。
 *
 * ## 这里补上的三态区分
 *
 * 抽取前这些列表**没有加载态**，`catch` 直接把数组清空 —— 于是"请求失败"与
 * "确实没有推荐"在界面上长得一模一样（都是"暂无…"）。这与仓库里已修过的另一处
 * 缺陷同类（见 `pages/ops/cdn.vue`）。现在每个列表都有 loading / failed 两态，
 * 失败时可以原地重试。
 *
 * 加载时机与原实现一致：
 *  - 挂载时加载与文章无关的公共数据（热门 / 趋势标签 / 为你推荐）；
 *  - 拿到 `articleId` 后（含"新建保存成功"后由 new 变为编辑）再加载依赖文章的两项。
 */
import {onMounted, reactive, ref, watch} from 'vue'

import {
  recommendApi,
  type RecommendArticleItem,
  type RecommendPopularItem,
  type RecommendRelatedItem,
  type RecommendScoredItem,
  type RecommendTagSuggestion,
  type RecommendTrendingTag,
} from '@/api'
import {formatDate} from '@/utils/format'

const props = defineProps<{
  /** 当前文章 id；新建（尚未保存）时为 null，依赖它的两项会提示"请先保存" */
  articleId: number | null
}>()

const emit = defineEmits<{
  /** 采纳一个建议标签（无权限时按钮已由 v-auth 隐藏） */
  (e: 'adopt', tag: string): void
}>()

const {t} = useI18n()

/** 五个标签页；同一个 key 兼作加载/失败状态的索引 */
type PanelKey = 'tags' | 'related' | 'popular' | 'trending' | 'forMe'

const assistTab = ref<PanelKey>('tags')

/** 标签建议（GET /content/recommend/tags/{article_id}） */
const tagSuggestions = ref<RecommendTagSuggestion[]>([])
/** 相关文章（GET /content/recommend/related/{article_id}） */
const relatedItems = ref<RecommendRelatedItem[]>([])
/** 热门文章（GET /content/recommend/popular） */
const popularItems = ref<RecommendPopularItem[]>([])
/** 热门文章口径说明（后端原样文案） */
const popularSource = ref('')
/** 热门标签（GET /content/recommend/trending-tags） */
const trendingItems = ref<RecommendTrendingTag[]>([])
/** 个性化推荐（GET /content/recommend/for-me） */
const forMeItems = ref<RecommendScoredItem[]>([])
/** 个性化推荐冷启动标记（无行为样本） */
const forMeColdStart = ref(false)

/** 每个面板各自的"加载中"标记 */
const loading = reactive<Record<PanelKey, boolean>>({
  tags: false,
  related: false,
  popular: false,
  trending: false,
  forMe: false,
})

/** 每个面板各自的"加载失败"标记 —— 用来把"失败"从"暂无"里区分出来 */
const failed = reactive<Record<PanelKey, boolean>>({
  tags: false,
  related: false,
  popular: false,
  trending: false,
  forMe: false,
})

/** 文章站内链接：有 slug 用 slug，否则回退到 id 路由（与前台卡片一致） */
function articleLink(item: RecommendArticleItem): string {
  return item.slug ? `/articles/${item.slug}` : `/articles/id/${item.id}`
}

async function loadTags(): Promise<void> {
  const id = props.articleId
  if (id === null) {
    tagSuggestions.value = []
    return
  }
  loading.tags = true
  failed.tags = false
  try {
    const result = await recommendApi.tagSuggestions(id, 10)
    tagSuggestions.value = result.suggestions ?? []
  } catch {
    tagSuggestions.value = []
    failed.tags = true
  } finally {
    loading.tags = false
  }
}

async function loadRelated(): Promise<void> {
  const id = props.articleId
  if (id === null) {
    relatedItems.value = []
    return
  }
  loading.related = true
  failed.related = false
  try {
    const result = await recommendApi.related(id, 8)
    relatedItems.value = result.items ?? []
  } catch {
    relatedItems.value = []
    failed.related = true
  } finally {
    loading.related = false
  }
}

async function loadPopular(): Promise<void> {
  loading.popular = true
  failed.popular = false
  try {
    const result = await recommendApi.popular(undefined, 10)
    popularItems.value = result.items ?? []
    popularSource.value = result.source ?? ''
  } catch {
    popularItems.value = []
    popularSource.value = ''
    failed.popular = true
  } finally {
    loading.popular = false
  }
}

async function loadTrendingTags(): Promise<void> {
  loading.trending = true
  failed.trending = false
  try {
    const result = await recommendApi.trendingTags(30, 20)
    trendingItems.value = result.items ?? []
  } catch {
    trendingItems.value = []
    failed.trending = true
  } finally {
    loading.trending = false
  }
}

async function loadForMe(): Promise<void> {
  loading.forMe = true
  failed.forMe = false
  try {
    const result = await recommendApi.forMe(10)
    forMeItems.value = result.items ?? []
    forMeColdStart.value = Boolean(result.cold_start)
  } catch {
    forMeItems.value = []
    forMeColdStart.value = false
    failed.forMe = true
  } finally {
    loading.forMe = false
  }
}

onMounted(() => {
  void loadPopular()
  void loadTrendingTags()
  void loadForMe()
  void loadTags()
  void loadRelated()
})

// 保存后拿到文章 id（新建 → 编辑）时，补齐依赖 article_id 的两项
watch(
  () => props.articleId,
  (id) => {
    if (id === null) return
    void loadTags()
    void loadRelated()
  },
)
</script>

<template>
  <el-card shadow="never">
    <template #header>{{ $t('admin.content.article.recommend.title') }}</template>

    <el-tabs v-model="assistTab">
      <el-tab-pane :label="$t('admin.content.article.recommend.tabTags')" name="tags">
        <p v-if="articleId === null" class="assist-hint">
          {{ $t('admin.content.article.recommend.saveFirst') }}
        </p>
        <p v-else-if="loading.tags" class="assist-hint">{{ $t('common.loading') }}</p>
        <div v-else-if="failed.tags" class="assist-failed">
          <span>{{ $t('admin.common.loadFailed') }}</span>
          <el-button link size="small" @click="loadTags">{{ $t('admin.common.retry') }}</el-button>
        </div>
        <p v-else-if="!tagSuggestions.length" class="assist-hint">
          {{ $t('admin.content.article.recommend.emptyTags') }}
        </p>
        <ul v-else class="assist-list">
          <li v-for="item in tagSuggestions" :key="item.tag" class="assist-row">
            <span class="assist-row__main">
              <span class="assist-row__title">{{ item.tag }}</span>
              <span class="assist-row__meta">
                <el-tag v-if="item.already_on_article" size="small" type="success">
                  {{ $t('admin.content.article.recommend.onArticle') }}
                </el-tag>
                <el-tag v-else-if="item.in_use" size="small" type="info">
                  {{ $t('admin.content.article.recommend.inLibrary') }}
                </el-tag>
                <span>{{ item.count }}</span>
              </span>
            </span>
            <el-button
              v-auth="'module_content:article:edit'"
              :disabled="item.already_on_article"
              link
              size="small"
              @click="emit('adopt', item.tag)"
            >
              {{ $t('admin.content.article.recommend.adopt') }}
            </el-button>
          </li>
        </ul>
      </el-tab-pane>

      <el-tab-pane :label="$t('admin.content.article.recommend.tabRelated')" name="related">
        <p v-if="articleId === null" class="assist-hint">
          {{ $t('admin.content.article.recommend.saveFirst') }}
        </p>
        <p v-else-if="loading.related" class="assist-hint">{{ $t('common.loading') }}</p>
        <div v-else-if="failed.related" class="assist-failed">
          <span>{{ $t('admin.common.loadFailed') }}</span>
          <el-button link size="small" @click="loadRelated">{{ $t('admin.common.retry') }}</el-button>
        </div>
        <p v-else-if="!relatedItems.length" class="assist-hint">
          {{ $t('admin.content.article.recommend.emptyRelated') }}
        </p>
        <ul v-else class="assist-list">
          <li v-for="item in relatedItems" :key="item.id" class="assist-row">
            <a :href="articleLink(item)" class="assist-row__link" rel="noopener" target="_blank">{{
                item.title
              }}</a>
            <span class="assist-row__meta">
              {{ formatDate(item.published_at) }} · {{ item.views }}
            </span>
          </li>
        </ul>
      </el-tab-pane>

      <el-tab-pane :label="$t('admin.content.article.recommend.tabPopular')" name="popular">
        <p v-if="popularSource" class="assist-hint">{{ popularSource }}</p>
        <p v-if="loading.popular" class="assist-hint">{{ $t('common.loading') }}</p>
        <div v-else-if="failed.popular" class="assist-failed">
          <span>{{ $t('admin.common.loadFailed') }}</span>
          <el-button link size="small" @click="loadPopular">{{ $t('admin.common.retry') }}</el-button>
        </div>
        <p v-else-if="!popularItems.length" class="assist-hint">
          {{ $t('admin.content.article.recommend.emptyPopular') }}
        </p>
        <ul v-else class="assist-list">
          <li v-for="item in popularItems" :key="item.id" class="assist-row">
            <a :href="articleLink(item)" class="assist-row__link" rel="noopener" target="_blank">{{
                item.title
              }}</a>
            <span class="assist-row__meta">
              {{ item.views }}
              <template v-if="item.window_views">
                · {{ $t('admin.content.article.recommend.windowViews', {n: item.window_views}) }}
              </template>
            </span>
          </li>
        </ul>
      </el-tab-pane>

      <el-tab-pane :label="$t('admin.content.article.recommend.tabTrending')" name="trending">
        <p v-if="loading.trending" class="assist-hint">{{ $t('common.loading') }}</p>
        <div v-else-if="failed.trending" class="assist-failed">
          <span>{{ $t('admin.common.loadFailed') }}</span>
          <el-button link size="small" @click="loadTrendingTags">{{ $t('admin.common.retry') }}</el-button>
        </div>
        <p v-else-if="!trendingItems.length" class="assist-hint">
          {{ $t('admin.content.article.recommend.emptyTrending') }}
        </p>
        <ul v-else class="assist-list">
          <li v-for="item in trendingItems" :key="item.tag" class="assist-row">
            <span class="assist-row__main">
              <span class="assist-row__title">{{ item.tag }}</span>
              <span class="assist-row__meta">{{ item.count }}</span>
            </span>
            <el-button
              v-auth="'module_content:article:edit'"
              link
              size="small"
              @click="emit('adopt', item.tag)"
            >
              {{ $t('admin.content.article.recommend.adopt') }}
            </el-button>
          </li>
        </ul>
      </el-tab-pane>

      <el-tab-pane :label="$t('admin.content.article.recommend.tabForMe')" name="forMe">
        <p v-if="forMeColdStart" class="assist-hint">
          {{ $t('admin.content.article.recommend.coldStart') }}
        </p>
        <p v-if="loading.forMe" class="assist-hint">{{ $t('common.loading') }}</p>
        <div v-else-if="failed.forMe" class="assist-failed">
          <span>{{ $t('admin.common.loadFailed') }}</span>
          <el-button link size="small" @click="loadForMe">{{ $t('admin.common.retry') }}</el-button>
        </div>
        <p v-else-if="!forMeItems.length" class="assist-hint">
          {{ $t('admin.content.article.recommend.emptyForMe') }}
        </p>
        <ul v-else class="assist-list">
          <li v-for="item in forMeItems" :key="item.id" class="assist-row">
            <a :href="articleLink(item)" class="assist-row__link" rel="noopener" target="_blank">{{
                item.title
              }}</a>
            <span class="assist-row__meta">{{ item.score }}</span>
          </li>
        </ul>
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<style scoped>
.assist-hint {
  margin: 0 0 var(--admin-gap-xs);
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

/* 加载失败：与"暂无数据"区分开，并给一个原地重试入口 */
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

.assist-row__title {
  font-size: 13px;
  font-weight: 500;
  color: var(--admin-fg);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.assist-row__link {
  font-size: 13px;
  color: var(--admin-primary, var(--admin-fg));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.assist-row__meta {
  display: inline-flex;
  gap: var(--admin-gap-xs);
  align-items: center;
  flex-shrink: 0;
  font-size: 12px;
  color: var(--admin-fg-subtle);
}
</style>
