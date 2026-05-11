import {Extension} from '@tiptap/core';

// 类型声明：扩展Tiptap的命令接口
declare module '@tiptap/core' {
    interface Commands<ReturnType> {
        textAlign: {
            /** 设置文本对齐方式 */
            setTextAlign: (alignment: 'left' | 'center' | 'right' | 'justify') => ReturnType;
            /** 重置为默认对齐方式 */
            unsetTextAlign: () => ReturnType;
        };
    }
}

export const TextAlignExtended = Extension.create({
    name: 'textAlignExtended',

    addOptions() {
        return {
            types: ['heading', 'paragraph'], // 应用对齐样式的节点类型
            defaultAlignment: 'left', // 默认对齐方式
        };
    },

    addGlobalAttributes() {
        return [
            {
                types: this.options.types, // 应用到的节点类型
                attributes: {
                    textAlign: {
                        // 默认值（从配置项获取）
                        default: this.options.defaultAlignment,
                        // 渲染到HTML时的处理
                        renderHTML: (attributes) => {
                            if (!attributes.textAlign || attributes.textAlign === this.options.defaultAlignment) {
                                return {};
                            }
                            // 将对齐方式转换为行内样式
                            return {
                                style: `text-align: ${attributes.textAlign};`,
                            };
                        },
                        // 从HTML解析时的处理
                        parseHTML: (element) => {
                            return {
                                // 获取对齐样式或使用默认值
                                textAlign: element.style.textAlign || this.options.defaultAlignment,
                            };
                        },
                    },
                },
            },
        ];
    },

    addCommands() {
        return {
            setTextAlign:
                (alignment) =>
                    ({tr, state, dispatch}) => {
                        // 验证对齐方式是否有效
                        const validAlignments = ['left', 'center', 'right', 'justify'];
                        if (!validAlignments.includes(alignment)) {
                            return false;
                        }

                        // 创建事务副本以保持不可变性
                        tr = tr.setSelection(state.selection);
                        // 遍历选区内的所有节点
                        state.doc.nodesBetween(state.selection.from, state.selection.to, (node, pos) => {
                            // 只处理配置的类型节点
                            if (this.options.types.includes(node.type.name)) {
                                tr = tr.setNodeMarkup(pos, undefined, {
                                    ...node.attrs,
                                    textAlign: alignment, // 更新对齐属性
                                });
                            }
                        });
                        // 提交事务更新
                        if (dispatch) {
                            dispatch(tr);
                        }
                        return true;
                    },
            unsetTextAlign:
                () =>
                    ({tr, state, dispatch}) => {
                        tr = tr.setSelection(state.selection);
                        // 遍历选区节点重置对齐方式
                        state.doc.nodesBetween(state.selection.from, state.selection.to, (node, pos) => {
                            if (this.options.types.includes(node.type.name)) {
                                tr = tr.setNodeMarkup(pos, undefined, {
                                    ...node.attrs,
                                    textAlign: this.options.defaultAlignment, // 重置为默认值
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