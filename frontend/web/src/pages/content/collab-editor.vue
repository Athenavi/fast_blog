<script lang="ts" setup>
/**
 * 协同编辑器（/content/collab-editor，content 域）
 *
 * **本页是 Yjs 实时协同的"用户可达面"**。此前后端已完备（`pycrdt` 真实 CRDT 合并、
 * y-protocols sync 三步、Redis 跨 worker 广播、鉴权与文档归属校验），但**前端没有任何
 * yjs 客户端** —— 也就是说"实时协同编辑"对用户根本不可用。本页 + `lib/yjs/collab-provider.ts`
 * 补上这一环。
 *
 * 数据流：
 *   正文初始值 ← `articleApi`（首人进入时若 CRDT 文档为空则填入，避免空房间）
 *   实时编辑   ← Y.Text ↔ textarea（**最小差量**同步，不整篇重写）
 *   落库       ← `yjsApi.saveSnapshot`（显式「保存到文章」按钮，不做隐式自动保存）
 *
 * 协议与鉴权见 provider 的文档注释（帧 = [type][payload]，token 走 query）。
 */
import * as Y from 'yjs'
import {computed, nextTick, onBeforeUnmount, ref, watch} from 'vue'

import {articleApi, yjsApi} from '@/api'
import {CollabProvider, type CollabStatus} from '@/lib/yjs/collab-provider'
import {ElMessage} from '@/utils/feedback'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.collabEditor.title',
  permission: 'module_content:collaboration:view',
})

const {t} = useI18n()

const docId = ref<number | null>(null)
const status = ref<CollabStatus>('connecting')
const statusDetail = ref('')
const online = ref(0)
const text = ref('')
const saving = ref(false)
const textarea = ref<HTMLTextAreaElement | null>(null)

let doc: Y.Doc | null = null
/** ⚠️ 必须是 ref：`joined` 由它派生，普通变量不会被 computed 追踪
 *  （曾因此导致 join() 后页面永远显示"未加入"、textarea 不渲染 —— type-check 抓不到这类错误） */
const provider = ref<CollabProvider | null>(null)
let yText: Y.Text | null = null
let observer: (() => void) | null = null
/** 已经尝试过用文章正文初始化（防止重复填入） */
let seeded = false

const joined = computed(() => provider.value !== null)
const statusLabel = computed(
  () =>
    ({
      connecting: t('admin.content.collabEditor.connecting'),
      connected: t('admin.content.collabEditor.connected'),
      synced: t('admin.content.collabEditor.synced'),
      disconnected: t('admin.content.collabEditor.disconnected'),
      rejected: t('admin.content.collabEditor.rejected'),
    })[status.value],
)
const statusClass = computed(() =>
  status.value === 'synced'
    ? 'text-success'
    : status.value === 'rejected'
      ? 'text-danger'
      : 'text-fg-subtle',
)

/** 用文章现有正文做首次初始化（仅当 CRDT 文档为空时） */
async function seedFromArticle(id: number): Promise<void> {
  if (seeded || !yText || !doc) return
  seeded = true
  if (yText.length > 0) return // 房间里已有内容（Redis 恢复 / 别人先到）
  try {
    const detail: any = await articleApi.detail(id)
    const content = String(detail?.content ?? detail?.article?.content ?? '')
    if (!content) return
    // 用**文档内的共享标记**保证只初始化一次：两端同时进来都插入正文会让内容翻倍
    // （实测出现过 "初始正文初始正文"）。标记是 CRDT 的一部分，会同步给另一端；
    // 并发窗口仍存在，但比无条件插入小得多。两个检查都在事务提交前完成。
    const meta = doc.getMap<boolean>('meta')
    if (meta.get('seeded') || yText.length > 0) return
    doc.transact(() => {
      meta.set('seeded', true)
      yText!.insert(0, content)
    })
  } catch {
    // 取不到正文不阻断协同（空文档也能开始编辑），但如实提示
    ElMessage.warning(t('admin.content.collabEditor.seedFailed'))
  }
}

function join(): void {
  const id = Number(docId.value)
  if (!id) {
    ElMessage.warning(t('admin.content.collabEditor.docRequired'))
    return
  }
  if (provider.value) leave()

  doc = new Y.Doc()
  yText = doc.getText('content')

  // Y.Text → 界面：**直接写 DOM**（非受控）。
  // 不用 `:value="text"` 受控绑定：用户输入、CRDT 同步、手动光标三者在 Vue 的受控
  // patch 下会互相覆盖（实测出现「Y.Text 已是 22 字符、DOM 仍为空」）。
  observer = () => {
    const next = yText!.toString()
    const el = textarea.value
    if (el && el.value !== next) el.value = next
    text.value = next // 仅供长度/诊断显示，不参与绑定
  }
  yText.observe(observer)

  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('fastblog.token') : null
  provider.value = new CollabProvider({
    documentId: id,
    doc,
    token,
    invite: new URLSearchParams(window.location.search).get('invite'),
  })
  provider.value.onStatus = (next, detail) => {
    status.value = next
    statusDetail.value = detail ?? ''
    online.value = provider.value?.peers().length ?? 0
    if (next === 'synced') {
      void seedFromArticle(id)
    }
  }
  provider.value.connect()
  ElMessage.info(t('admin.content.collabEditor.joining'))
}

function leave(): void {
  if (yText && observer) yText.unobserve(observer)
  provider.value?.destroy()
  provider.value = null
  doc = null
  yText = null
  observer = null
  seeded = false
  text.value = ''
  online.value = 0
  status.value = 'connecting'
  statusDetail.value = ''
}

/** textarea 输入 → 计算与 Y.Text 的**最小差量**后应用（整篇重写会让远端光标乱跳） */
function onInput(): void {
  if (!yText || !doc) {
    // 不该发生（textarea 只在 joined 时渲染）；显式报出来而不是静默丢弃输入
    console.warn('[collab] onInput 触发但协同未就绪（yText/doc 为空），输入被忽略')
    return
  }
  const next = textarea.value?.value ?? ''
  const prev = yText.toString()
  console.log(`[collab] onInput prevLen=${prev.length} nextLen=${next.length}`)
  if (prev === next) return

  let start = 0
  while (start < prev.length && start < next.length && prev[start] === next[start]) start++
  let endPrev = prev.length
  let endNext = next.length
  while (endPrev > start && endNext > start && prev[endPrev - 1] === next[endNext - 1]) {
    endPrev--
    endNext--
  }

  const caret = start + (endNext - start)
  doc.transact(() => {
    if (endPrev > start) yText!.delete(start, endPrev - start)
    const inserted = next.slice(start, endNext)
    if (inserted) yText!.insert(start, inserted)
  })
  text.value = yText.toString()
  console.log(`[collab] after insert yTextLen=${yText.length} textLen=${text.value.length}`)
  void nextTick(() => textarea.value?.setSelectionRange(caret, caret))
}

/** 纯文本 → 段落化 HTML。
 *
 * 后端 `save_snapshot` 收的是** HTML 快照**（`YjsSnapshotPayload.html`），而本页编辑器是
 * 纯文本 textarea → 这里按空行分段、段内换行转 `<br>`，并转义 HTML 特殊字符。
 */
function textToHtml(value: string): string {
  const escape = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return value
    .split(/\n{2,}/)
    .map((para) => `<p>${escape(para).replace(/\n/g, '<br>')}</p>`)
    .join('\n')
}

/** 把当前协同内容保存到文章（后端 `save_snapshot` 落 article_content） */
async function save(): Promise<void> {
  if (!provider.value || !yText || !docId.value) return
  saving.value = true
  try {
    await yjsApi.saveSnapshot(Number(docId.value), {html: textToHtml(yText.toString())})
    ElMessage.success(t('admin.content.collabEditor.saved'))
  } catch {
    // http 层已提示
  } finally {
    saving.value = false
  }
}

/** textarea 是 `v-if="joined"` 渲染的：元素一旦重建（重连、条件抖动），DOM 会回到空白
 *  而 Y.Text 仍有内容 —— 但 observer 只在 Y.Text **变化**时触发，不会再写回来。
 *  这里在 joined 变为 true（含重建）后主动把 Y.Text 的内容写进 DOM。 */
watch(joined, async (isJoined) => {
  if (!isJoined) return
  await nextTick()
  const next = yText?.toString() ?? ''
  const el = textarea.value
  if (el && el.value !== next) el.value = next
})

onBeforeUnmount(leave)
</script>

<template>
  <AdminPage :desc="t('admin.content.collabEditor.desc')" :title="t('admin.content.collabEditor.title')">
    <template #actions>
      <button
        :disabled="saving || !joined"
        class="rounded-md bg-primary px-3 py-1.5 text-sm text-white disabled:opacity-50"
        type="button"
        @click="save"
      >
        {{ saving ? t('common.submitting') : t('admin.content.collabEditor.save') }}
      </button>
    </template>

    <div class="space-y-4">
      <!-- 目标与状态 -->
      <div class="flex flex-wrap items-end gap-2">
        <label class="text-sm">
          <span class="mb-1 block text-fg-subtle">{{ t('admin.content.collabEditor.docLabel') }}</span>
          <input
            v-model.number="docId"
            class="w-32 rounded border border-default px-3 py-1.5 text-sm"
            min="1"
            type="number"
          >
        </label>

        <button
          v-if="!joined"
          :disabled="!docId"
          class="rounded-md bg-primary px-3 py-1.5 text-sm text-white disabled:opacity-50"
          type="button"
          @click="join"
        >
          {{ t('admin.content.collabEditor.join') }}
        </button>
        <button
          v-else
          class="rounded-md border border-default px-3 py-1.5 text-sm"
          type="button"
          @click="leave"
        >
          {{ t('admin.content.collabEditor.leave') }}
        </button>

        <span v-if="joined" :class="statusClass" class="text-sm">
          {{ statusLabel }}
          <span v-if="statusDetail" class="text-fg-subtle">（{{ statusDetail }}）</span>
        </span>
        <span v-if="joined" class="text-sm text-fg-subtle">
          {{ t('admin.content.collabEditor.online', {count: online}) }}
        </span>
      </div>

      <!-- 协作编辑区 -->
      <textarea
        v-if="joined"
        ref="textarea"
        :placeholder="t('admin.content.collabEditor.placeholder')"
        class="h-[60vh] w-full rounded-lg border border-default p-3 font-mono text-sm"
        @input="onInput"
      />

      <div v-else class="rounded-lg bg-surface-soft p-4 text-sm text-fg-subtle">
        {{ t('admin.content.collabEditor.hint') }}
      </div>
    </div>
  </AdminPage>
</template>
