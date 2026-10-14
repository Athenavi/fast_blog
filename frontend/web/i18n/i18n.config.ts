import zhCN from './site/zh-CN.json'

/**
 * vue-i18n 配置：**默认语言（zh-CN）的前台文案在构建期内联**。
 *
 * 这里的 `messages` 会直接打进 bundle，首屏就有文案、不需要等任何请求。
 *
 * `./site/zh-CN.json` 是构建期派生物，由 `scripts/split-i18n.mjs` 从真相源
 * `i18n/locales/zh-CN.json` 生成，只含前台命名空间。后台的 `admin` 命名空间
 * 占全部文案的 77.5%（zh-CN 约 187 KB），已拆到 `public/i18n/admin/`，
 * 由 `layouts/admin.vue` 在进入后台时按需加载。
 *
 * ⚠️ 为什么 `locales[].file` 仍指向一个**空占位**（`i18n/messages/zh-CN.json` = `{}`）：
 * `@nuxtjs/i18n` 有硬校验「使用 `langDir` 时每个 locale 都必须有 `file`/`files`」
 * （模块 `checkLayerOptions`），而 `loadMessagesFromServer` 的入口是
 * `if (locale in localeLoaders === false) return` —— 只要有 `file` 就必然发一次
 * `messages.json` 请求，**躲不掉**。既然躲不掉，就让默认语言这次请求的响应体
 * 小到可忽略（空对象 merge 进去无任何影响），真正的文案走这里的构建期内联。
 * 这一步把该请求从 193 KB raw / 66 KB gzip 降到约 3 字节。
 *
 * 非默认语言 `en` 不在内联范围内：它保留为 lazy file，切到英文时才加载
 * （中文站 `detectBrowserLanguage: false`，没必要为英文文案给每个访客的 bundle 加体积）。
 */
export default defineI18nConfig(() => ({
  messages: {
    'zh-CN': zhCN,
  },
}))
