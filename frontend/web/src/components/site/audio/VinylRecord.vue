<script lang="ts" setup>
const {t} = useI18n()
/**
 * 黑胶唱片 + 唱臂
 *
 * 对应 astro 版 `AudioPlayer/VinylRecord.tsx`。原实现用 framer-motion 做
 * 唱臂摆动、唱片自转与辉光脉冲；这里改成**纯 CSS 动画/过渡**，不引入动画库，
 * 交互与视觉保持一致（点击唱片最小化）。
 *
 * 颜色说明：这是**播放器皮肤**（黑底 + 紫粉渐变，与 astro 版设计一致），
 * 和 `ThemeSwitcher` 的色板同属「必须显示自身配色」的例外，不走语义令牌。
 */
withDefaults(
  defineProps<{
    coverImage?: string | null
    loading?: boolean
    isPlaying?: boolean
  }>(),
  {coverImage: null, loading: false, isPlaying: false},
)

const emit = defineEmits<{ (e: 'minimize'): void }>()

/** 唱片纹路：与原来一致的 7 圈 */
const GROOVES = [5, 10, 15, 20, 25, 30, 35] as const
</script>

<template>
  <div class="relative hidden w-[45%] items-center justify-center overflow-hidden lg:flex">
    <!-- 背景辉光 -->
    <div
      :style="{opacity: isPlaying ? 0.3 : 0.06}"
      class="absolute inset-0 transition-opacity duration-1000"
    >
      <div
        :class="{ 'is-playing': isPlaying }"
        class="vinyl-glow absolute left-1/2 top-1/2 aspect-square w-[120%] -translate-x-1/2 -translate-y-1/2 rounded-full blur-3xl"/>
    </div>

    <!-- 唱片 + 唱臂（点击唱片最小化） -->
    <div
      class="relative cursor-pointer"
      role="button"
      tabindex="0"
      :title="$t('audio.minimizeTitle')"
      @click="emit('minimize')"
      @keyup.enter="emit('minimize')"
    >
      <!-- 唱臂 -->
      <div
        :class="{ 'is-playing': isPlaying }"
        class="vinyl-arm absolute -right-8 -top-8 z-10 origin-[16px_100%]"
      >
        <svg fill="none" height="48" viewBox="0 0 110 48" width="110">
          <rect fill="url(#armGrad)" height="4" rx="2" width="94" x="16" y="10"/>
          <circle cx="16" cy="12" fill="#555" r="10" stroke="#333" stroke-width="1.5"/>
          <circle cx="16" cy="12" fill="#222" r="4"/>
          <circle cx="16" cy="12" fill="#888" r="1.5"/>
          <rect fill="#555" height="20" rx="3" width="18" x="92" y="2"/>
          <circle cx="101" cy="12" fill="#777" r="3"/>
          <defs>
            <linearGradient id="armGrad" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0%" stop-color="#999"/>
              <stop offset="50%" stop-color="#666"/>
              <stop offset="100%" stop-color="#444"/>
            </linearGradient>
          </defs>
        </svg>
      </div>

      <!-- 黑胶唱片 -->
      <div
        :class="{ 'vinyl-disc is-playing': isPlaying }"
        :style="{
          boxShadow: isPlaying
            ? '0 0 100px rgba(147, 51, 234, 0.35), inset 0 0 80px rgba(0,0,0,0.6)'
            : '0 0 50px rgba(147, 51, 234, 0.1), inset 0 0 80px rgba(0,0,0,0.6)',
        }"
        class="relative flex h-72 w-72 items-center justify-center rounded-full bg-gradient-to-br from-gray-800 via-gray-900 to-black xl:h-80 xl:w-80"
      >
        <!-- 纹路 -->
        <div
          v-for="inset in GROOVES"
          :key="inset"
          :style="{inset: `${inset * 4}px`}"
          class="absolute rounded-full border border-gray-700/20"
        />
        <!-- 反光 -->
        <div
          class="pointer-events-none absolute inset-2 rounded-full bg-gradient-to-br from-white/[0.06] via-transparent to-transparent"/>

        <!-- 中心标签 -->
        <div class="relative z-10 h-28 w-28 overflow-hidden rounded-full ring-2 ring-white/10 xl:h-32 xl:w-32">
          <img v-if="coverImage" :alt="t('audio.cover')" :src="coverImage" class="h-full w-full object-cover"
               decoding="async">
          <div v-else
               class="flex h-full w-full items-center justify-center bg-gradient-to-br from-purple-600 to-pink-600">
            <span v-if="loading" class="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent"/>
            <Icon v-else class="h-7 w-7 text-white/80" name="music"/>
          </div>
        </div>

        <!-- 中心孔 -->
        <div class="absolute z-20 h-3 w-3 rounded-full border border-gray-700/50 bg-black"/>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 唱片自转：暂停时用 animation-play-state 停在原处（与 framer-motion 的
   「停下并保留角度」行为接近；原实现其实是复位到 0，这里保留角度观感更自然） */
.vinyl-disc.is-playing {
  animation: vinyl-spin 8s linear infinite;
}

@keyframes vinyl-spin {
  to {
    transform: rotate(360deg);
  }
}

/* 唱臂：按下播放 → 摆到盘面（18deg），暂停 → 抬回（-35deg） */
.vinyl-arm {
  transform: rotate(-35deg);
  transition: transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.vinyl-arm.is-playing {
  transform: rotate(18deg);
}

/* 辉光：播放时缓慢呼吸 */
.vinyl-glow {
  background: radial-gradient(circle, rgba(147, 51, 234, 0.5), rgba(236, 72, 153, 0.2), transparent);
  opacity: 0.2;
  transition: opacity 0.6s ease;
}

.vinyl-glow.is-playing {
  animation: vinyl-glow-pulse 4s ease-in-out infinite;
}

@keyframes vinyl-glow-pulse {
  0%,
  100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.3;
  }

  50% {
    transform: translate(-50%, -50%) scale(1.1);
    opacity: 0.6;
  }
}

@media (prefers-reduced-motion: reduce) {
  .vinyl-disc.is-playing,
  .vinyl-glow.is-playing {
    animation: none;
  }
}
</style>
