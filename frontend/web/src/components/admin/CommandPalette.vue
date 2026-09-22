<script lang="ts" setup>
/**
 * 后台命令面板（⌘K / Ctrl+K）
 *
 * 为什么是后台体验里性价比最高的一块：侧边栏有 10 组、50+ 项菜单，
 * 用鼠标在树里逐层找是纯摩擦。这里把所有"可跳转的页面"和"高频动作"拉平到一个检索框，
 * 再配合 ⌘K 一键唤起 —— 手不离键盘就能到达任意页面。
 *
 * 数据来源：
 *  - 页面：`permissionStore.menus`（已按权限 + 后端菜单授权过滤过，因此天然不会越权）；
 *  - 最近访问：`useRecentPages()`（localStorage，最多 6 条，命中率最高的一档）；
 *  - 动作：新建文章 / 打开前台站点 / 切换深浅色，无权限时保留在列表里并标注，而不是消失。
 *
 * 交互：↑↓ 选择、Enter 打开、Esc 关闭（Esc 由 el-dialog 处理）、鼠标悬停同步高亮。
 */
import {computed, nextTick, ref, watch} from 'vue'

import {flattenMenuTargets, menuLabel} from '@/utils/menus'
import {useRecentPages} from '@/composables/useRecentPages'
import {useTheme} from '@/composables/useTheme'
import {useAppStore} from '@/store/modules/app'
import {usePermissionStore} from '@/store/modules/permission'
import {useUserStore} from '@/store/modules/user'

type GroupKey = 'recent' | 'pages' | 'actions'

interface CommandItem {
  id: string
  label: string
  /** 右侧辅助说明：所属分组或快捷键 */
  hint: string
  group: GroupKey
  icon: string
  /** 无权限的条目仍然展示（可解释），但不可执行 */
  allowed: boolean
  run: () => void | Promise<void>
}

const appStore = useAppStore()
const permissionStore = usePermissionStore()
const userStore = useUserStore()
const {isDark, toggleDark} = useTheme()
const {t, te} = useI18n()
const router = useRouter()

const {pages: recentPaths, hydrate: hydrateRecent, remember} = useRecentPages()

const keyword = ref('')
const activeIndex = ref(0)
const inputRef = ref<HTMLInputElement | null>(null)
const listRef = ref<HTMLElement | null>(null)

const GROUP_TITLE: Record<GroupKey, string> = {
  recent: 'admin.command.recent',
  pages: 'admin.command.pages',
  actions: 'admin.command.actions',
}

// ---------------------------------------------------------------- 条目构建
const pageItems = computed<CommandItem[]>(() =>
  flattenMenuTargets(permissionStore.menus).map(({item, parentTitle, parentIcon}) => ({
    id: `page:${item.path}`,
    label: menuLabel(item, (key) => t(key), (key) => te(key)),
    hint: parentTitle,
    group: 'pages' as const,
    icon: parentIcon || 'Document',
    allowed: true,
    run: () => {
      remember(item.path)
      void router.push(item.path)
    },
  })),
)

const recentItems = computed<CommandItem[]>(() => {
  const byPath = new Map(pageItems.value.map((entry) => [entry.id, entry]))
  return recentPaths.value
    .map((path) => byPath.get(`page:${path}`))
    .filter((entry): entry is CommandItem => Boolean(entry))
    .map((entry) => ({...entry, group: 'recent' as const, hint: t('admin.command.recent')}))
})

const actionItems = computed<CommandItem[]>(() => {
  const canCreateArticle = userStore.hasPermission('module_content:article:create')
  const canViewArticle = userStore.hasPermission('module_content:article:view')
  return [
    {
      id: 'action:new-article',
      label: t('admin.content.article.newArticle'),
      hint: canCreateArticle ? '' : t('admin.command.disabledNoPermission'),
      group: 'actions' as const,
      icon: 'Plus',
      allowed: canCreateArticle && canViewArticle,
      run: () => {
        remember('/content/article')
        void router.push('/content/article/new')
      },
    },
    {
      id: 'action:open-site',
      label: t('nav.backToFront'),
      hint: '',
      group: 'actions' as const,
      icon: 'Promotion',
      allowed: true,
      run: () => {
        window.open('/', '_blank', 'noopener')
      },
    },
    {
      id: 'action:toggle-theme',
      label: t('admin.theme.toggle'),
      hint: isDark.value ? t('admin.theme.light') : t('admin.theme.dark'),
      group: 'actions' as const,
      icon: isDark.value ? 'Sunny' : 'Moon',
      allowed: true,
      run: () => {
        toggleDark()
      },
    },
  ]
})

/** 未检索时"最近访问"排在前面（最常用），检索时不参与匹配 */
const matched = computed<CommandItem[]>(() => {
  const words = keyword.value.trim().toLowerCase()

  if (words) {
    return [...pageItems.value, ...actionItems.value].filter((entry) =>
      `${entry.label} ${entry.hint}`.toLowerCase().includes(words),
    )
  }

  // 未检索时："最近访问"置顶，并从"页面"里去掉已出现过的项（同一个入口不重复列两次）
  const recentIds = new Set(recentItems.value.map((entry) => entry.id))
  return [
    ...recentItems.value,
    ...pageItems.value.filter((entry) => !recentIds.has(entry.id)),
    ...actionItems.value,
  ]
})

// ---------------------------------------------------------------- 键盘导航
watch(keyword, () => {
  activeIndex.value = 0
})

function move(step: number): void {
  if (!matched.value.length) return
  const next = activeIndex.value + step
  activeIndex.value = Math.min(Math.max(next, 0), matched.value.length - 1)
  void nextTick(() => {
    listRef.value?.querySelector<HTMLElement>(`[data-index="${activeIndex.value}"]`)?.scrollIntoView({block: 'nearest'})
  })
}

async function run(entry: CommandItem): Promise<void> {
  if (!entry.allowed) return
  appStore.closeCommandPalette()
  await entry.run()
}

function runActive(): void {
  const entry = matched.value[activeIndex.value]
  if (entry) void run(entry)
}

// ---------------------------------------------------------------- 开关
watch(
  () => appStore.commandPaletteOpen,
  (open) => {
    if (!open) return
    keyword.value = ''
    activeIndex.value = 0
    hydrateRecent()
  },
)

function onOpened(): void {
  void nextTick(() => inputRef.value?.focus())
}

function onClosed(): void {
  keyword.value = ''
  activeIndex.value = 0
}

/** ⌘K / Ctrl+K 全局唤起（后台页面内随时可用） */
function onGlobalKeydown(event: KeyboardEvent): void {
  if (!(event.ctrlKey || event.metaKey) || event.shiftKey || event.altKey) return
  if (event.key.toLowerCase() !== 'k') return
  event.preventDefault()
  appStore.toggleCommandPalette()
}

onMounted(() => window.addEventListener('keydown', onGlobalKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onGlobalKeydown))
</script>

<template>
  <el-dialog
    v-model="appStore.commandPaletteOpen"
    :show-close="false"
    align-center
    append-to-body
    class="cmdk"
    width="min(600px, 94vw)"
    @closed="onClosed"
    @opened="onOpened"
  >
    <div class="cmdk__search">
      <el-icon class="cmdk__search-icon">
        <Search/>
      </el-icon>
      <input
        ref="inputRef"
        v-model="keyword"
        :aria-label="$t('admin.command.open')"
        :placeholder="$t('admin.command.placeholder')"
        class="cmdk__input"
        type="text"
        @keydown.down.prevent="move(1)"
        @keydown.enter.prevent="runActive"
        @keydown.up.prevent="move(-1)"
      >
    </div>

    <p v-if="!matched.length" class="cmdk__empty">{{ $t('admin.command.empty') }}</p>

    <ul v-else ref="listRef" class="cmdk__list">
      <template v-for="(entry, index) in matched" :key="entry.id">
        <li v-if="index === 0 || matched[index - 1]?.group !== entry.group" class="cmdk__group-title">
          {{ $t(GROUP_TITLE[entry.group]) }}
        </li>
        <li>
          <button
            :aria-selected="index === activeIndex"
            :class="{'is-active': index === activeIndex, 'is-denied': !entry.allowed}"
            :data-index="index"
            role="option"
            type="button"
            @click="run(entry)"
            @mousemove="activeIndex = index"
          >
            <el-icon class="cmdk__item-icon">
              <component :is="entry.icon"/>
            </el-icon>
            <span class="cmdk__item-label">{{ entry.label }}</span>
            <span v-if="entry.hint" class="cmdk__item-hint">{{ entry.hint }}</span>
          </button>
        </li>
      </template>
    </ul>

    <p class="cmdk__footer">{{ $t('admin.command.keyboardHint') }}</p>
  </el-dialog>
</template>

<style scoped>
/*
 * 注意：`.cmdk` 的 class 落在 Element Plus 的 `.el-dialog` 元素上（组件内部节点），
 * 父组件的 scoped 规则匹配不到它，所以"去标题栏"那两条写在 `styles/admin.css`。
 */
.cmdk__search {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--admin-line);
}

.cmdk__search-icon {
  color: var(--admin-fg-subtle);
}

.cmdk__input {
  flex: 1;
  font-size: 15px;
  color: var(--admin-fg);
  background: transparent;
  border: none;
  outline: none;
}

.cmdk__input::placeholder {
  color: var(--admin-fg-subtle);
}

.cmdk__list {
  max-height: min(52vh, 420px);
  padding: 6px;
  margin: 0;
  overflow-y: auto;
  list-style: none;
}

.cmdk__group-title {
  padding: 8px 10px 4px;
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

.cmdk__list button {
  display: flex;
  gap: 10px;
  align-items: center;
  width: 100%;
  padding: 8px 10px;
  color: var(--admin-fg);
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: none;
  border-radius: var(--admin-radius-sm);
}

.cmdk__list button.is-active {
  background: var(--admin-primary-soft);
}

.cmdk__list button.is-denied {
  color: var(--admin-fg-subtle);
  cursor: not-allowed;
}

.cmdk__item-icon {
  color: var(--admin-fg-muted);
}

.cmdk__item-label {
  flex: 1;
  font-size: 14px;
}

.cmdk__item-hint {
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

.cmdk__empty {
  padding: 28px 16px;
  font-size: var(--admin-font-sm);
  color: var(--admin-fg-subtle);
  text-align: center;
}

.cmdk__footer {
  padding: 8px 16px;
  font-size: 12px;
  color: var(--admin-fg-subtle);
  border-top: 1px solid var(--admin-line);
}
</style>
