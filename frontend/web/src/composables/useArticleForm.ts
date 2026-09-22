import {computed, onBeforeUnmount, onMounted, reactive, ref, type ComputedRef, type Ref, watch} from 'vue'

import {articleApi, mobileApi, type ArticlePayload, type MobileArticlePayload} from '@/api'
import {formatDateTime} from '@/utils/format'

/**
 * 文章表单状态与读写（UI/UX 路线图 Batch 1.1）
 *
 * 为什么抽出来：后台编辑页（`pages/content/article/[id].vue`）与前台投稿页
 * （`components/site/ArticleEditor.vue`）此前各写了一遍"字段定义 + 加载 + 保存 + 校验"，
 * 于是同一个产品里同一批字段出现两种缺省值、两种空值处理、两种报错文案；删字段时
 * 还得记得改两处。现在两边共用这一份逻辑。
 *
 * **刻意不统一的部分**：渲染层仍然分开（后台 Element Plus + `--admin-*` 令牌、前台
 * Tailwind + `components/ui/*`），这是既有取舍 —— 强行统一两套 UI 体系得不偿失；
 * 分类选项也由调用方注入，因为两者的数据源权限不同（后台 `categoryApi` / 前台
 * `mobileApi` 公开树）。
 *
 * 两种模式：
 *   - `admin`：全量字段（状态/定时发布/置顶/推荐/隐藏/VIP/排序），可用 `publishNow()`
 *   - `contributor`：仅内容字段 + VIP 可见性，后端 schema **不接受**管理字段，只能存草稿
 */

export interface ArticleContentFields {
  title: string
  slug: string
  excerpt: string
  content: string
  cover_image: string
  category_id: number | null
  tags: string[]
  is_vip_only: boolean
  required_vip_level: number
}

/** 仅管理端可见/可写（投稿模式不涉及，后端也不接受） */
export interface ArticlePublishFields {
  status: number
  hidden: boolean
  is_featured: boolean
  is_sticky: boolean
  post_type: string
  sort_order: number
  scheduled_publish_at: string | null
}

export type ArticleFormMode = 'admin' | 'contributor'

/** 文案由调用方注入，composable 不碰 UI 文案与提示组件 */
export interface ArticleFormMessages {
  titleRequired: string
  saveFailed: string
  loadFailed: string
}

export interface UseArticleFormOptions {
  mode: ArticleFormMode
  /** 当前文章 id（`null` = 新建）；传 ref 或 getter 都行 */
  articleId?: Ref<number | null> | (() => number | null)
  messages: ArticleFormMessages
}

export interface SaveResult {
  ok: boolean
  /** 保存后的文章 id（新建时由后端返回） */
  id: number | null
}

/** 本地暂存的未保存内容（刷新/关标签页/崩溃后仍可恢复） */
export interface LocalArticleDraft {
  /** 暂存时间（ISO 字符串） */
  savedAt: string
  form: ArticleContentFields
  publish: ArticlePublishFields
}

export interface UseArticleFormReturn {
  form: ArticleContentFields
  publish: ArticlePublishFields
  loading: Ref<boolean>
  saving: Ref<boolean>
  dirty: Ref<boolean>
  savedAt: Ref<string | null>
  notFound: Ref<boolean>
  error: Ref<string>
  /** 启动时发现的本地暂存内容（由页面决定"恢复"还是"丢弃"） */
  draftAvailable: Ref<LocalArticleDraft | null>
  isNew: ComputedRef<boolean>
  markDirty: () => void
  load: () => Promise<void>
  save: (statusOverride?: number) => Promise<SaveResult>
  saveDraft: () => Promise<SaveResult>
  publishNow: () => Promise<SaveResult>
  restoreDraft: () => void
  discardDraft: () => void
}

function emptyContent(): ArticleContentFields {
  return {
    title: '',
    slug: '',
    excerpt: '',
    content: '',
    cover_image: '',
    category_id: null,
    tags: [],
    is_vip_only: false,
    required_vip_level: 0,
  }
}

function emptyPublish(): ArticlePublishFields {
  return {
    status: 0,
    hidden: false,
    is_featured: false,
    is_sticky: false,
    post_type: 'article',
    sort_order: 0,
    scheduled_publish_at: null,
  }
}

const asText = (value: unknown): string => (typeof value === 'string' ? value : '')
const asNumber = (value: unknown, fallback = 0): number => (typeof value === 'number' ? value : fallback)
const asBool = (value: unknown): boolean => value === true

/** 本地草稿存储键前缀（按 模式 + 文章 id 区分，互不覆盖） */
const DRAFT_STORAGE_PREFIX = 'fb-article-draft'
/** 编辑期自动暂存的防抖时长（毫秒） */
const DRAFT_WRITE_DELAY = 1500

export function useArticleForm(options: UseArticleFormOptions): UseArticleFormReturn {
  const form = reactive<ArticleContentFields>(emptyContent())
  const publish = reactive<ArticlePublishFields>(emptyPublish())

  const loading = ref(false)
  const saving = ref(false)
  const dirty = ref(false)
  const savedAt = ref<string | null>(null)
  const notFound = ref(false)
  const error = ref('')

  const resolveId = (): number | null => {
    const raw = typeof options.articleId === 'function' ? options.articleId() : options.articleId?.value
    return raw ?? null
  }

  const isNew = computed(() => resolveId() === null)

  function markDirty(): void {
    dirty.value = true
  }

  // ---------------------------------------------------------------- 本地草稿
  /**
   * 只在客户端存在：编辑期防抖把"未保存内容"写进 localStorage，
   * 刷新、误关标签页、崩溃后还能拿回来。保存成功即清除。
   * `onBeforeRouteLeave` 只能拦住站内跳转，拦不住刷新与关标签页，因此这里还要配 `beforeunload`。
   */
  const draftAvailable = ref<LocalArticleDraft | null>(null)

  function draftKey(): string {
    return `${DRAFT_STORAGE_PREFIX}:${options.mode}:${resolveId() ?? 'new'}`
  }

  function readDraft(): LocalArticleDraft | null {
    if (!import.meta.client) return null
    try {
      const raw = window.localStorage.getItem(draftKey())
      if (!raw) return null
      const parsed = JSON.parse(raw) as Partial<LocalArticleDraft>
      if (!parsed?.form || typeof parsed.savedAt !== 'string') return null
      return {
        savedAt: parsed.savedAt,
        form: {...emptyContent(), ...parsed.form},
        publish: {...emptyPublish(), ...parsed.publish},
      }
    } catch {
      // 结构损坏的旧草稿：视作没有，不影响进入编辑页
      return null
    }
  }

  function writeDraft(): void {
    if (!import.meta.client || !dirty.value) return
    try {
      const payload: LocalArticleDraft = {
        savedAt: new Date().toISOString(),
        form: {...form},
        publish: {...publish},
      }
      window.localStorage.setItem(draftKey(), JSON.stringify(payload))
    } catch {
      /* 隐私模式/配额不足：静默降级，不影响正常编辑 */
    }
  }

  function clearDraft(): void {
    draftAvailable.value = null
    if (!import.meta.client) return
    try {
      window.localStorage.removeItem(draftKey())
    } catch {
      /* 同上 */
    }
  }

  /** 用户选择"恢复"：覆盖当前表单，并保持脏标记（内容尚未写进服务端） */
  function restoreDraft(): void {
    const draft = draftAvailable.value
    if (!draft) return
    Object.assign(form, draft.form)
    Object.assign(publish, draft.publish)
    dirty.value = true
    draftAvailable.value = null
  }

  /** 用户选择"丢弃" */
  function discardDraft(): void {
    clearDraft()
  }

  if (import.meta.client) {
    let draftTimer: ReturnType<typeof setTimeout> | null = null

    watch(
      [form, publish],
      () => {
        if (!dirty.value) return
        if (draftTimer) clearTimeout(draftTimer)
        draftTimer = setTimeout(writeDraft, DRAFT_WRITE_DELAY)
      },
      {deep: true},
    )

    const confirmUnload = (event: BeforeUnloadEvent): void => {
      if (!dirty.value) return
      writeDraft() // 不等防抖，立刻落盘
      event.preventDefault()
      event.returnValue = ''
    }

    onMounted(() => window.addEventListener('beforeunload', confirmUnload))
    onBeforeUnmount(() => {
      window.removeEventListener('beforeunload', confirmUnload)
      if (draftTimer) clearTimeout(draftTimer)
    })
  }

  function applyContent(source: Record<string, unknown>): void {
    form.title = asText(source.title)
    form.slug = asText(source.slug)
    form.excerpt = asText(source.excerpt)
    form.content = asText(source.content)
    form.cover_image = asText(source.cover_image)
    form.category_id = typeof source.category_id === 'number' ? source.category_id : null
    form.tags = Array.isArray(source.tags) ? source.tags.map((item) => String(item)) : []
    form.is_vip_only = asBool(source.is_vip_only)
    form.required_vip_level = asNumber(source.required_vip_level)
  }

  function applyPublish(source: Record<string, unknown>): void {
    publish.status = asNumber(source.status)
    publish.hidden = asBool(source.hidden)
    publish.is_featured = asBool(source.is_featured)
    publish.is_sticky = asBool(source.is_sticky)
    publish.post_type = asText(source.post_type) || 'article'
    publish.sort_order = asNumber(source.sort_order)
    publish.scheduled_publish_at = typeof source.scheduled_publish_at === 'string' ? source.scheduled_publish_at : null
  }

  async function load(): Promise<void> {
    const id = resolveId()
    if (id === null) {
      Object.assign(form, emptyContent())
      Object.assign(publish, emptyPublish())
      dirty.value = false
      draftAvailable.value = readDraft()
      return
    }

    loading.value = true
    notFound.value = false
    error.value = ''
    try {
      const detail =
        options.mode === 'admin' ? await articleApi.detail(id) : await mobileApi.myArticleDetail(id)
      applyContent({...detail})
      if (options.mode === 'admin') applyPublish({...detail})
      dirty.value = false
    } catch {
      // 投稿模式下的 404 = 不是本人的文章（后端按归属过滤），与"文章不存在"同义
      notFound.value = true
      error.value = options.messages.loadFailed
    } finally {
      loading.value = false
      draftAvailable.value = readDraft()
    }
  }

  function buildAdminPayload(title: string, statusOverride?: number): ArticlePayload {
    return {
      title,
      slug: form.slug.trim() || undefined,
      excerpt: form.excerpt.trim() || undefined,
      content: form.content,
      cover_image: form.cover_image.trim() || undefined,
      category_id: form.category_id,
      tags: form.tags,
      is_vip_only: form.is_vip_only,
      required_vip_level: Number(form.required_vip_level) || 0,
      status: statusOverride ?? publish.status,
      hidden: publish.hidden,
      is_featured: publish.is_featured,
      is_sticky: publish.is_sticky,
      post_type: publish.post_type,
      sort_order: publish.sort_order,
      scheduled_publish_at: publish.scheduled_publish_at || null,
    }
  }

  function buildContributorPayload(title: string): MobileArticlePayload {
    return {
      title,
      slug: form.slug.trim() || undefined,
      excerpt: form.excerpt.trim() || undefined,
      content: form.content,
      cover_image: form.cover_image.trim() || undefined,
      category_id: form.category_id,
      tags: form.tags,
      is_vip_only: form.is_vip_only,
      required_vip_level: Number(form.required_vip_level) || 0,
    }
  }

  async function save(statusOverride?: number): Promise<SaveResult> {
    error.value = ''

    const title = form.title.trim()
    if (!title) {
      error.value = options.messages.titleRequired
      return {ok: false, id: null}
    }

    saving.value = true
    try {
      const id = resolveId()
      let savedId = id

      if (options.mode === 'admin') {
        const payload = buildAdminPayload(title, statusOverride)
        if (id === null) {
          savedId = (await articleApi.create(payload)).id
        } else {
          await articleApi.update(id, payload)
        }
        if (savedId !== null) publish.status = payload.status ?? publish.status
      } else {
        const payload = buildContributorPayload(title)
        if (id === null) {
          savedId = (await mobileApi.createDraft(payload)).id
        } else {
          await mobileApi.updateMyArticle(id, payload)
        }
      }

      dirty.value = false
      savedAt.value = formatDateTime(new Date().toISOString())
      clearDraft()
      return {ok: true, id: savedId}
    } catch {
      error.value = options.messages.saveFailed
      return {ok: false, id: null}
    } finally {
      saving.value = false
    }
  }

  const saveDraft = () => save(0)

  async function publishNow(): Promise<SaveResult> {
    if (options.mode !== 'admin') {
      // 投稿不能自助发布：后端 schema 不接受 status，发布由管理员执行
      error.value = options.messages.saveFailed
      return {ok: false, id: null}
    }

    const result = await save(1)
    if (!result.ok || result.id === null) return result

    try {
      await articleApi.publish(result.id, true)
    } catch {
      error.value = options.messages.saveFailed
      return {ok: false, id: result.id}
    }
    return result
  }

  return {
    form,
    publish,
    loading,
    saving,
    dirty,
    savedAt,
    notFound,
    error,
    draftAvailable,
    isNew,
    markDirty,
    load,
    save,
    saveDraft,
    publishNow,
    restoreDraft,
    discardDraft,
  }
}
