import {ref, type Ref, watch} from 'vue'

import {CODE_SUCCESS} from '@/composables/useApi'
import {STORAGE_TOKEN} from '@/constants'
import {storage} from '@/utils/storage'
import type {LyricLine} from '@/components/site/audio/helpers'

/**
 * 音频元数据（封面 + 歌词）
 *
 * 数据源：`GET /api/v3/mobile/media/{id}/metadata`（T5-10 已自 v2 收敛到 v3），
 * 需登录、本人或公开媒体可读；响应形状（cover_image / lyrics）与 v2 一致。
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
    const token = storage.get<string>(STORAGE_TOKEN)
    try {
      const result = await $fetch<{
        code?: number
        data?: { cover_image?: string | null; lyrics?: LyricLine[] } | null
      }>(`/api/v3/mobile/media/${id}/metadata`, {
        credentials: 'include',
        headers: token ? {Authorization: `Bearer ${token}`} : {},
      })

      if (result?.code === CODE_SUCCESS && result.data) {
        coverImage.value = result.data.cover_image ?? null
        lyrics.value = Array.isArray(result.data.lyrics) ? result.data.lyrics : []
      } else {
        coverImage.value = null
        lyrics.value = []
      }
    } catch {
      // 元数据取不到不影响播放（与 astro 版行为一致）
      error.value = 'audio-unavailable'
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
