import {Extension} from '@tiptap/core';

// 类型声明：扩展Tiptap的命令接口
declare module '@tiptap/core' {
    interface Commands<ReturnType> {
        letterSpacing: {
            /** 设置字母间距 */
            setLetterSpacing: (spacing: string) => ReturnType;
            /** 重置为默认字母间距 */
            unsetLetterSpacing: () => ReturnType;
        };
    }
}

export const LetterSpacing = Extension.create({
    name: 'letterSpacing',

    addOptions() {
        return {
            types: ['textStyle'], // 应用字母间距样式的节点类型
            defaultSpacing: null, // 默认字母间距（null表示不设置）
        };
    },

    addGlobalAttributes() {
        return [
            {
                types: this.options.types, // 应用到的节点类型
                attributes: {
                    letterSpacing: {
                        // 默认值（从配置项获取）
                        default: this.options.defaultSpacing,
                        // 渲染到HTML时的处理
                        renderHTML: (attributes) => {
                            if (!attributes.letterSpacing) {
                                return {};
                            }
                            // 将字母间距转换为行内样式
                            return {
                                style: `letter-spacing: ${attributes.letterSpacing};`,
                            };
                        },
                        // 从HTML解析时的处理
                        parseHTML: (element) => {
                            return {
                                // 获取字母间距样式或使用默认值
                                letterSpacing: element.style.letterSpacing || this.options.defaultSpacing,
                            };
                        },
                    },
                },
            },
        ];
    },

    addCommands() {
        return {
            setLetterSpacing:
                (spacing) =>
                    ({tr, state, dispatch}) => {
                        // 创建事务副本以保持不可变性
                        tr = tr.setSelection(state.selection);
                        // 遍历选区内的所有节点
                        state.doc.nodesBetween(state.selection.from, state.selection.to, (node, pos) => {
                            // 只处理配置的类型节点
                            if (this.options.types.includes(node.type.name)) {
                                tr = tr.setNodeMarkup(pos, undefined, {
                                    ...node.attrs,
                                    letterSpacing: spacing, // 更新字母间距属性
                                });
                            }
                        });
                        // 提交事务更新
                        if (dispatch) {
                            dispatch(tr);
                        }
                        return true;
                    },
            unsetLetterSpacing:
                () =>
                    ({tr, state, dispatch}) => {
                        tr = tr.setSelection(state.selection);
                        // 遍历选区节点重置字母间距
                        state.doc.nodesBetween(state.selection.from, state.selection.to, (node, pos) => {
                            if (this.options.types.includes(node.type.name)) {
                                tr = tr.setNodeMarkup(pos, undefined, {
                                    ...node.attrs,
                                    letterSpacing: this.options.defaultSpacing, // 重置为默认值
                                });
                            }
                        });
                        if (dispatch) {
                            dispatch(tr);
                        }
                        return true;
                    },
        };
    },
});