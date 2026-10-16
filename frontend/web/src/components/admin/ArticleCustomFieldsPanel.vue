<script lang="ts" setup>
/**
 * 文章自定义字段面板
 *
 * 后端早就支持自定义字段（`custom_post_type` 模块：类型 CRUD + `GET/PUT
 * /{type_id}/values/{content_id}`，含 `field_spec.py` 的完整定义校验与取值校验），
 * 但此前**只有一个孤立的管理页** `content/custom-field-values.vue` ——
 * 要在那里人工选「类型 + 内容 ID」再填值。也就是说：写文章时填不了自定义字段，
 * 得先发布、记住 ID、再跑到另一个页面去填。这个组件把入口补回写作现场。
 *
 * ## 两个约束决定了这里的实现方式
 *
 * 1. **文章是内置类型，没有 `type_id`**。字段定义挂在内容类型上，所以用
 *    **`slug` 约定**：约定 `slug === 'article'` 的内容类型即为文章提供字段。
 *    没有这样的类型时**整个面板不渲染**（`hasFields` 为 false），
 *    完全不影响现有写作流程 —— 而不是显示一个空卡片让人猜。
 *
 * 2. **新建文章时还没有 `content_id`**。字段值只能挂在已存在的内容实例上，
 *    所以保存时机是「父页保存文章 → 拿到 id → 调本组件的 `save(id)`」，
 *    与 WordPress 的 ACF 一致（先有 post ID）。因此这里用 `defineExpose`
 *    暴露 `save()`，而不是自己带一个保存按钮。
 *
 * ## 两种字段类型做了降级，理由写在这里
 *
 * - `richtext`：本项目正文用 Tiptap，但字段值在后端是**纯文本列**存储。
 *   塞 HTML 进字段值会绕过正文那条「服务端渲染 + 净化」的链路，反而制造
 *   XSS 面。故降级为多行文本，并提示用户富文本请写正文。
 * - `relation`：后端只给 `target`（如 `tag`/`category`）作为语义提示，
 *   没有提供「按 target 拉候选列表」的统一接口，硬做会变成对每种 target
 *   各写一套。故降级为文本输入，并显示 target 作为填写提示。
 */
import {computed, ref, watch} from 'vue'

import {type CustomFieldEntry, customPostTypeApi, type CustomPostTypeItem} from '@/api'
import {ElMessage} from '@/utils/feedback'

const props = defineProps<{
  /** 当前文章 id；新建（未保存）时为 null，此时只渲染定义、不拉值 */
  articleId: number | null
}>()

/** 约定：`slug === 'article'` 的内容类型即为文章提供自定义字段 */
const ARTICLE_TYPE_SLUG = 'article'

const {t} = useI18n()

const loading = ref(false)
const saving = ref(false)
const failed = ref(false)
const postType = ref<CustomPostTypeItem | null>(null)
/** 解析后的字段定义（后端 `fields` 是 JSON 字符串） */
const definitions = ref<CustomFieldEntry[]>([])
/** 字段值：{key: value}；未填字段由后端按定义补 null */
const values = ref<Record<string, unknown>>({})

/** 没有匹配的内容类型、或该类型没定义字段时不渲染面板 */
const hasFields = computed(() => definitions.value.length > 0)

/** `fields` 是 JSON 字符串，解析失败不该让整页崩 —— 当作"没定义字段" */
function parseDefinitions(raw: unknown): CustomFieldEntry[] {
  if (typeof raw !== 'string' || !raw.trim()) return []
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? (parsed as CustomFieldEntry[]) : []
  } catch {
    return []
  }
}

/** 找到为文章提供字段的内容类型 */
async function loadType(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    const page = await customPostTypeApi.list({page: 1, page_size: 100})
    const items = (page?.items ?? []) as CustomPostTypeItem[]
    const matched = items.find((item) => item.slug === ARTICLE_TYPE_SLUG && item.is_active)
    postType.value = matched ?? null
    definitions.value = matched ? parseDefinitions(matched.fields) : []
  } catch {
    // 后端不可用：不渲染面板，而不是弹一个用户无法处理的错误
    failed.value = true
    postType.value = null
    definitions.value = []
  } finally {
    loading.value = false
  }
}

/** 拉已有字段值（仅当文章已保存且类型定义了字段时） */
async function loadValues(): Promise<void> {
  const typeId = postType.value?.id
  if (!typeId || !props.articleId || !hasFields.value) return
  try {
    const result = await customPostTypeApi.getValues(typeId, props.articleId)
    values.value = {...(result?.values ?? {})}
  } catch {
    // 取值失败时保留空值：用户仍可重新填写并保存
    values.value = {}
  }
}

async function reload(): Promise<void> {
  await loadType()
  await loadValues()
}

await reload()

// 新建文章保存成功后，父页会把 articleId 从 null 变为真实 id —— 此时补拉一次值
watch(
  () => props.articleId,
  async (next, prev) => {
    if (next && next !== prev) await loadValues()
  },
)

/**
 * 保存字段值（由父页在文章保存成功后调用）
 *
 * **不回滚文章**：字段值写失败时文章已经存下了，回滚只会丢掉用户的正文。
 * 这里只提示，让用户能单独重试。
 *
 * @returns 是否成功（父页据此决定要不要再提示一次）
 */
async function save(contentId: number): Promise<boolean> {
  const typeId = postType.value?.id
  // 没有类型或没有字段定义 → 无事可做，视为成功（不该因此报错）
  if (!typeId || !hasFields.value) return true

  saving.value = true
  try {
    await customPostTypeApi.setValues(typeId, contentId, values.value)
    return true
  } catch {
    ElMessage.warning(String(t('admin.content.article.customFields.saveFailed')))
    return false
  } finally {
    saving.value = false
  }
}

/** i18n：组件在 <script> 里取 t，与页面保持一致 */
defineExpose({save, reload})
</script>

<template>
  <el-card v-if="hasFields" v-loading="loading || saving" shadow="never">
    <template #header>{{ $t('admin.content.article.customFields.title') }}</template>

    <el-alert
      v-if="failed"
      :closable="false"
      :title="$t('admin.content.article.customFields.loadFailed')"
      type="warning"
    />

    <!-- 新建文章尚未保存：字段值需要挂在已存在的内容实例上 -->
    <p v-else-if="!articleId" class="custom-fields__hint">
      {{ $t('admin.content.article.customFields.saveFirst') }}
    </p>

    <el-form label-position="top">
      <el-form-item
        v-for="field in definitions"
        :key="field.key"
        :label="field.label || field.key"
      >
        <!-- select：可多选（多选值以 JSON 数组存） -->
        <el-select
          v-if="field.type === 'select'"
          v-model="values[field.key]"
          :multiple="!!field.multiple"
          :placeholder="$t('admin.content.article.customFields.selectPlaceholder')"
          class="custom-fields__control"
        >
          <el-option
            v-for="option in field.options ?? []"
            :key="option"
            :label="option"
            :value="option"
          />
        </el-select>

        <!-- boolean -->
        <el-switch v-else-if="field.type === 'boolean'" v-model="values[field.key]"/>

        <!-- number：带上定义里的 min/max，避免用户填完才被后端拒 -->
        <el-input-number
          v-else-if="field.type === 'number'"
          v-model="values[field.key]"
          :max="field.max ?? undefined"
          :min="field.min ?? undefined"
        />

        <!-- date -->
        <el-date-picker
          v-else-if="field.type === 'date'"
          v-model="values[field.key]"
          type="date"
          value-format="YYYY-MM-DD"
        />

        <!-- json：等宽字体，便于看结构 -->
        <el-input
          v-else-if="field.type === 'json'"
          v-model="values[field.key]"
          :rows="3"
          class="custom-fields__mono"
          type="textarea"
        />

        <!-- textarea / richtext 降级 -->
        <el-input
          v-else-if="field.type === 'textarea' || field.type === 'richtext'"
          v-model="values[field.key]"
          :rows="3"
          type="textarea"
        />

        <!-- text / url / email / relation 降级：统一单行输入，url/email 用对应键盘 -->
        <el-input
          v-else
          v-model="values[field.key]"
          :type="field.type === 'url' || field.type === 'email' ? field.type : 'text'"
        />

        <p v-if="field.help" class="form-hint">{{ field.help }}</p>
        <p v-if="field.type === 'richtext'" class="form-hint">
          {{ $t('admin.content.article.customFields.richtextHint') }}
        </p>
        <p v-if="field.type === 'relation' && field.target" class="form-hint">
          {{ $t('admin.content.article.customFields.relationHint', {target: field.target}) }}
        </p>
        <p v-if="field.required" class="form-hint">
          {{ $t('admin.content.article.customFields.requiredHint') }}
        </p>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<style scoped>
/* select / input-number / date-picker 默认不撑满，与其它表单项宽度不一致 */
.custom-fields__control {
  width: 100%;
}

.custom-fields__mono :deep(textarea) {
  font-family: var(--admin-font-mono, ui-monospace, SFMono-Regular, Menlo, monospace);
}

.custom-fields__hint {
  margin: 0 0 12px;
  color: var(--admin-text-subtle);
  font-size: 13px;
}
</style>
