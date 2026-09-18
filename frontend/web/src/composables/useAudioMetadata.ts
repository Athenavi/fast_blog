import {ref, type Ref, watch} from 'vue'

import type {LyricLine} from '@/components/site/audio/helpers'

/**
 * 音频元数据（封面 + 歌词）
 *
 * ⚠️ **数据源是 v2 兼容层**：`GET /api/v2/media/{id}/metadata`。
 * v3 的 `MediaItem` 里没有 `lyrics` / `cover_image` 字段，目前没有等价端点，
 * 细节与待办见 `docs/refactor/FUTURE_WORK_PLAN.md` §5。后端补上 v3 端点后，
 * 只需要改这一个函数。
 *
 * astro 原实现里 `AudioLayer`、`PlayerView`、`MiniPlayerWrapper` **各请求了一次**
 * 同一个接口（3 次重复请求）；这里合并为一次，由 `AudioLayer` 调用并向下传递。
 */
export function useAudioMetadata(mediaId: Ref<number | null>) {
  const coverImage = ref<string | null>(null)
  const lyrics = ref<LyricLine[]>([])
  const loading = ref(false)
  const error = ref('')

  async function load(id: number): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const result = await $fetch<{
        success?: boolean
        data?: { cover_image?: string | null; lyrics?: LyricLine[] }
      }>(`/api/v2/media/${id}/metadata`, {credentials: 'include'})

      if (result?.data) {
        coverImage.value = result.data.cover_image ?? null
        lyrics.value = Array.isArray(result.data.lyrics) ? result.data.lyrics : []
      } else {
        coverImage.value = null
        lyrics.value = []
      }
    } catch {
      // 元数据取不到不影响播放（与 astro 版行为一致）
      error.value = '音频元数据不可用'
      coverImage.value = null
      lyrics.value = []
    } finally {
      loading.value = false
    }
  }

  watch(
    mediaId,
    (id) => {
      if (id != null) void load(id)
    },
    {immediate: true},
  )

  return {coverImage, lyrics, loading, error}
}
