import {Node, mergeAttributes} from '@tiptap/core'

/**
 * 提示块（callout）
 *
 * 为什么值得加：技术/说明类内容里"注意、警告、成功"这类强调段落此前只能靠
 * 引用块（blockquote）表达，视觉上区分不出来。这里给一个语义化节点：
 * 输出 `<div data-callout="warning">…</div>`，样式由语义令牌驱动
 * （深浅色与自选配色自动跟随），前后台共用一套规则。
 */
export type CalloutType = 'info' | 'warning' | 'success' | 'danger'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    callout: {
      /** 把当前块包成提示块；已在提示块内则取消包裹 */
      toggleCallout: (attributes?: { type?: CalloutType }) => ReturnType
    }
  }
}

export const Callout = Node.create({
  name: 'callout',
  group: 'block',
  content: 'block+',
  defining: true,

  addAttributes() {
    return {
      type: {
        default: 'info' satisfies CalloutType,
        parseHTML: (element) => element.getAttribute('data-callout') || 'info',
        renderHTML: (attributes) => ({'data-callout': attributes.type as string}),
      },
    }
  },

  parseHTML() {
    return [{tag: 'div[data-callout]'}]
  },

  renderHTML({HTMLAttributes}) {
    return ['div', mergeAttributes(HTMLAttributes), 0]
  },

  addCommands() {
    return {
      toggleCallout:
        (attributes = {}) =>
          ({commands}) =>
            commands.toggleWrap(this.name, attributes),
    }
  },
})
