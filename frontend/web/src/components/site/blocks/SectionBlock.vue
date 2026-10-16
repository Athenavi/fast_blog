<script lang="ts" setup>
/**
 * 区块：section —— 通用区块容器
 *
 * 参数：
 *  - `padding`（`none` | `sm` | `md` | `lg`），默认 `md`
 *  - `background`（`none` | `surface` | `soft`），默认 `none`
 *  - `divider`（布尔），是否与上一区块之间加一条分隔线
 *
 * 只映射到站点既有令牌（`bg-surface` / `border-line`），主题想要别的观感
 * 应在自己的 `styles.css` 里覆盖，而不是让站点为它硬编码颜色。
 */
import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const PADDING_CLASS: Record<string, string> = {
  none: '',
  sm: 'py-6',
  md: 'py-10',
  lg: 'py-16',
  // 更宽松的档位：Halo 这类主题靠大留白建立节奏，WP 只用到 lg
  xl: 'py-20',
  '2xl': 'py-28',
  '3xl': 'py-36',
}

const BACKGROUND_CLASS: Record<string, string> = {
  none: '',
  surface: 'bg-surface',
  soft: 'bg-surface-soft',
}

function pick(map: Record<string, string>, raw: unknown, fallback: string): string {
  if (typeof raw === 'string' && map[raw]) return map[raw]
  return map[fallback] ?? ''
}

const paddingClass = computed(() => pick(PADDING_CLASS, props.propsData.padding, 'md'))
const backgroundClass = computed(() =>
  pick(BACKGROUND_CLASS, props.propsData.background, 'none'),
)
const dividerClass = computed(() => (props.propsData.divider === true ? 'border-t border-line' : ''))
</script>

<template>
  <section :class="[paddingClass, backgroundClass, dividerClass, props.blockClass]">
    <slot/>
  </section>
</template>
