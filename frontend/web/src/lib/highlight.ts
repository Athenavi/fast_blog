/**
 * 代码高亮（highlight.js + lowlight）
 *
 * 为什么需要：这是一套「技术博客 + CMS」，但正文代码块此前是纯黑字 ——
 * 全项目既没有 `highlight.js`/`shiki`/`prism` 依赖，编辑器也没做代码语言标注
 * （`katex-render` 插件只负责数学公式）。
 *
 * 两个消费方共用同一份语言注册表：
 *  - **编辑器**：`CodeBlockLowlight` 用 `lowlight` 做输入时实时高亮；
 *  - **前台正文**：`ArticleDetailView` 用 `hljs.highlightElement()` 对 SSR 出来的
 *    `<pre><code>` 做一次客户端高亮。
 *
 * 体积控制：只注册常用语言（不是 `highlight.js` 的全量 ~190 种），
 * 且本模块只被**动态 import**（没有代码块的页面不会下载它）。
 */
import bash from 'highlight.js/lib/languages/bash'
import css from 'highlight.js/lib/languages/css'
import hljs from 'highlight.js/lib/core'
import go from 'highlight.js/lib/languages/go'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import markdown from 'highlight.js/lib/languages/markdown'
import python from 'highlight.js/lib/languages/python'
import rust from 'highlight.js/lib/languages/rust'
import shell from 'highlight.js/lib/languages/shell'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'
import {createLowlight} from 'lowlight'

/** 语言别名 → highlight.js 语言定义（覆盖博客/文档里绝大多数代码块） */
const LANGUAGES = {
  bash,
  css,
  go,
  java,
  javascript,
  json,
  markdown,
  python,
  rust,
  shell,
  sql,
  typescript,
  xml,
  yaml,
}

/** 编辑器用（lowlight 实例） */
export const lowlight = createLowlight()

for (const [name, definition] of Object.entries(LANGUAGES)) {
  lowlight.register(name, definition)
  hljs.registerLanguage(name, definition)
}

/** 前台正文用（DOM 高亮） */
export {hljs}
