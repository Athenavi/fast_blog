<script lang="ts" setup>
/**
 * 文章历史（右侧抽屉 + 全屏差异浮层）
 *
 * ## 形态
 *
 * - **历史列表**：**右侧抽屉，默认关闭**，点触发按钮才滑出。常驻侧栏会永久占用
 *   编辑区宽度，而"看历史"是低频动作，不该跟正文抢空间。
 * - **版本比较**：**全屏浮层，左右分栏**。逐行 diff 需要横向空间放"旧行号 | 新行号 |
 *   变更标记 | 内容"四列，抽屉里放不下。
 *
 * ## 全部原生实现
 *
 * 编辑页在 `layout: 'default'`（前台布局）下，**没有注册 Element Plus** ——
 * 用 `el-drawer` / `el-dialog` 会静默解析失败（控制台只有一条 warn，界面什么都不出）。
 * 所以抽屉与浮层都用 `<Teleport>` + `fixed` 自己搭。
 *
 * ## 关于"恢复"的语义
 *
 * 后端 `restoreVersion` **不改写历史** —— 它把指定版本作为**新的一版**写回，
 * 所以"恢复"本身也可回溯（同 Git `revert`，不是 `reset --hard`）。文案如实写明。
 *
 * ## 接口一律走 `@/api/modules/yjs` 的封装，不手拼路径
 *
 * （手拼 `yjs/.../save` 时漏过模块段导致 404，有前车之鉴。）
 */
import {yjsApi, type YjsRevision, type YjsRevisionDetail} from '@/api'
import {type DiffLine, diffLines, diffStat} from '@/utils/diff'

const props = defineProps<{
  articleId: number
  /** 非作者访问时需要（邀请链接进入时带） */
  invite?: string | null
}>()

const emit = defineEmits<{
  /** 把某版本正文交给父级填进编辑器 */
  (e: 'restore', content: string): void
}>()

const {t} = useI18n()

// ---------------------------------------------------------------- 抽屉

const open = ref(false)
const compareOpen = ref(false)

const versions = ref<YjsRevision[]>([])
const loading = ref(false)
const failed = ref(false)

const leftNo = ref<number | null>(null)
const rightNo = ref<number | null>(null)
const detailCache = new Map<number, YjsRevisionDetail>()

const diff = ref<DiffLine[] | null>(null)
const stat = ref({added: 0, removed: 0})
const comparing = ref(false)

async function loadVersions(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    const page = await yjsApi.listVersions(props.articleId, {page: 1, page_size: 50, invite: props.invite})
    // `PageResult` 的字段是 `items`（见 `api/types.ts:24`）
    versions.value = [...(page?.items ?? [])].sort(
      (a, b) => (b.revision_number ?? 0) - (a.revision_number ?? 0),
    )
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

/** 打开抽屉时才拉数据 —— 低频动作不该在进页面时就发请求 */
function toggle(): void {
  open.value = !open.value
  if (open.value && !versions.value.length && !failed.value) void loadVersions()
}

async function loadDetail(revision: number): Promise<YjsRevisionDetail | null> {
  const cached = detailCache.get(revision)
  if (cached) return cached
  try {
    const detail = await yjsApi.getVersion(props.articleId, revision, props.invite)
    detailCache.set(revision, detail)
    return detail
  } catch {
    return null
  }
}

function pick(revision: number): void {
  if (leftNo.value === null || rightNo.value !== null) {
    leftNo.value = revision
    rightNo.value = null
    return
  }
  if (revision === leftNo.value) return
  rightNo.value = revision
}

async function compare(): Promise<void> {
  if (leftNo.value === null || rightNo.value === null) return
  comparing.value = true
  try {
    const [a, b] = await Promise.all([loadDetail(leftNo.value), loadDetail(rightNo.value)])
    if (!a || !b) {
      pushToast(t('myPosts.collab.history.loadVersionFailed'), 'error')
      return
    }
    diff.value = diffLines(a.content ?? '', b.content ?? '')
    stat.value = diffStat(diff.value)
    compareOpen.value = true
  } finally {
    comparing.value = false
  }
}

async function restore(revision: number): Promise<void> {
  const detail = await loadDetail(revision)
  if (!detail) {
    pushToast(t('myPosts.collab.history.loadVersionFailed'), 'error')
    return
  }
  try {
    // `YjsRestorePayload` 只有 `change_summary`（正文由后端按版本号自己读）
    await yjsApi.restoreVersion(
      props.articleId,
      revision,
      {change_summary: t('myPosts.collab.history.restoreSummary', {n: revision})},
      props.invite,
    )
    emit('restore', detail.content ?? '')
    pushToast(t('myPosts.collab.history.restored', {n: revision}), 'success')
    open.value = false
    await loadVersions()
  } catch {
    // 请求层已统一提示
  }
}

function fmtDate(value: string | null | undefined): string {
  if (!value) return ''
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString()
}

/** Esc 关闭（键盘可达性） */
function onKeydown(e: KeyboardEvent): void {
  if (e.key !== 'Escape') return
  if (compareOpen.value) compareOpen.value = false
  else if (open.value) open.value = false
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <!-- 触发按钮：常驻但不占版面 -->
  <button class="hist-trigger" type="button" @click="toggle">
    {{ t('myPosts.collab.history.title') }}
  </button>

  <Teleport to="body">
    <!-- 抽屉 -->
    <div v-if="open" class="hist-mask" @click.self="open = false">
      <aside aria-modal="true" class="hist-drawer" role="dialog">
        <header class="hist-drawer__head">
          <strong>{{ t('myPosts.collab.history.title') }}</strong>
          <div class="hist-drawer__actions">
            <button :disabled="loading" class="hist-btn" type="button" @click="loadVersions">
              {{ t('myPosts.collab.history.refresh') }}
            </button>
            <button class="hist-btn" type="button" @click="open = false">
              {{ t('myPosts.collab.history.close') }}
            </button>
          </div>
        </header>

        <div v-if="loading" class="hist-empty">{{ t('myPosts.collab.history.loading') }}</div>
        <div v-else-if="failed" class="hist-empty hist-empty--err">
          {{ t('myPosts.collab.history.loadFailed') }}
          <button class="hist-btn" type="button" @click="loadVersions">
            {{ t('myPosts.collab.history.retry') }}
          </button>
        </div>
        <div v-else-if="!versions.length" class="hist-empty">{{ t('myPosts.collab.history.empty') }}</div>

        <template v-else>
          <p class="hist-hint">{{ t('myPosts.collab.history.pickHint') }}</p>

          <ul class="hist-list">
            <li
              v-for="v in versions"
              :key="v.id"
              :class="{
                'is-left': v.revision_number === leftNo,
                'is-right': v.revision_number === rightNo,
              }"
              class="hist-item"
            >
              <button class="hist-pick" type="button" @click="pick(v.revision_number ?? 0)">
                <span class="hist-no">#{{ v.revision_number }}</span>
                <span class="hist-meta">
                  <span class="hist-title">{{ v.title || t('myPosts.collab.history.untitled') }}</span>
                  <span class="hist-sub">
                    {{ v.author_name || '—' }} · {{ v.content_chars }}{{ t('myPosts.collab.history.charsSuffix') }}
                    <template v-if="v.change_summary"> · {{ v.change_summary }}</template>
                  </span>
                </span>
              </button>
              <button class="hist-btn hist-btn--restore" type="button" @click="restore(v.revision_number ?? 0)">
                {{ t('myPosts.collab.history.restore') }}
              </button>
            </li>
          </ul>

          <footer class="hist-drawer__foot">
            <span class="hist-sub">
              {{
                leftNo === null ? t('myPosts.collab.history.pickLeft')
                  : rightNo === null ? t('myPosts.collab.history.pickRight')
                    : t('myPosts.collab.history.ready')
              }}
            </span>
            <button
              :disabled="leftNo === null || rightNo === null || comparing"
              class="hist-btn hist-btn--primary"
              type="button"
              @click="compare"
            >
              {{ t('myPosts.collab.history.compareAction') }}
            </button>
          </footer>
        </template>
      </aside>
    </div>

    <!-- 全屏差异浮层：左右分栏 -->
    <div v-if="compareOpen && diff" class="hist-full">
      <header class="hist-full__head">
        <strong>{{ t('myPosts.collab.history.compareTitle', {a: leftNo, b: rightNo}) }}</strong>
        <span class="hist-stat">
          <em class="hist-add">+{{ stat.added }}</em>
          <em class="hist-del">−{{ stat.removed }}</em>
        </span>
        <button class="hist-btn" type="button" @click="compareOpen = false">
          {{ t('myPosts.collab.history.close') }}
        </button>
      </header>

      <!-- 列头：旧版本 | 新版本 -->
      <div class="hist-full__cols">
        <span>#{{ leftNo }}</span>
        <span>#{{ rightNo }}</span>
      </div>

      <div class="hist-full__body">
        <div v-for="(line, idx) in diff" :key="idx" :class="`is-${line.kind}`" class="hist-row">
          <span class="hist-ln">{{ line.oldLine ?? '' }}</span>
          <span class="hist-ln">{{ line.newLine ?? '' }}</span>
          <span class="hist-sign">{{ line.kind === 'add' ? '+' : line.kind === 'remove' ? '−' : ' ' }}</span>
          <code class="hist-code">{{ line.text || ' ' }}</code>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.hist-trigger {
  align-self: flex-start;
  padding: 6px 14px;
  border: 1px solid var(--el-border-color, #dcdfe6);
  border-radius: 4px;
  background: #fff;
  color: #606266;
  font-size: 13px;
  cursor: pointer;
}

.hist-mask {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgb(0 0 0 / 0.35);
  display: flex;
  justify-content: flex-end;
}

.hist-drawer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: min(420px, 92vw);
  height: 100%;
  padding: 16px;
  background: #fff;
  box-shadow: -4px 0 16px rgb(0 0 0 / 0.12);
  overflow: auto;
}

.hist-drawer__head,
.hist-drawer__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.hist-drawer__actions {
  display: flex;
  gap: 6px;
}

.hist-hint,
.hist-sub {
  font-size: 12px;
  color: #909399;
}

.hist-empty {
  padding: 24px 8px;
  text-align: center;
  font-size: 12px;
  color: #909399;
}

.hist-empty--err {
  color: #f56c6c;
}

.hist-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.hist-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border: 1px solid transparent;
  border-radius: 4px;
}

/* 选中的两版用红/绿，与 diff 的增删配色对应 */
.hist-item.is-left {
  border-color: #f56c6c;
  background: #fef0f0;
}

.hist-item.is-right {
  border-color: #67c23a;
  background: #f0f9eb;
}

.hist-pick {
  display: flex;
  flex: 1;
  gap: 8px;
  min-width: 0;
  border: none;
  background: none;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.hist-no {
  flex-shrink: 0;
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: #606266;
}

.hist-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.hist-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: #303133;
}

.hist-btn {
  flex-shrink: 0;
  padding: 2px 8px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #fff;
  color: #606266;
  font-size: 12px;
  cursor: pointer;
}

.hist-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.hist-btn--primary {
  border-color: #2271b1;
  background: #2271b1;
  color: #fff;
}

.hist-btn:focus-visible,
.hist-pick:focus-visible,
.hist-trigger:focus-visible {
  outline: 2px solid #2271b1;
  outline-offset: 2px;
}

/* 全屏浮层 */
.hist-full {
  position: fixed;
  inset: 0;
  z-index: 2100;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.hist-full__head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid #ebeef5;
}

.hist-full__head strong {
  flex: 1;
}

.hist-stat {
  font-family: ui-monospace, monospace;
  font-size: 12px;
}

.hist-add {
  color: #67c23a;
  font-style: normal;
}

.hist-del {
  color: #f56c6c;
  font-style: normal;
  margin-left: 6px;
}

.hist-full__cols {
  display: grid;
  grid-template-columns: 5ch 5ch 2ch;
  gap: 8px;
  padding: 4px 12px;
  border-bottom: 1px solid #ebeef5;
  font-family: ui-monospace, monospace;
  font-size: 11px;
  color: #a8abb2;
}

.hist-full__body {
  flex: 1;
  overflow: auto;
  padding: 4px 0;
}

.hist-row {
  display: grid;
  grid-template-columns: 5ch 5ch 2ch minmax(0, 1fr);
  gap: 8px;
  padding: 0 12px;
  font-size: 12.5px;
  line-height: 1.65;
}

.hist-row.is-add {
  background: #f0f9eb;
}

.hist-row.is-remove {
  background: #fef0f0;
}

.hist-ln {
  color: #a8abb2;
  text-align: right;
  user-select: none;
}

.hist-sign {
  user-select: none;
}

.hist-code {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, monospace;
}
</style>
