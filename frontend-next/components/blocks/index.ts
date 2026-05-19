/**
 * Block 组件库导出
 */

export { default as ParagraphBlock } from './ParagraphBlock';
export { default as HeadingBlock } from './HeadingBlock';
export { default as SeparatorBlock } from './SeparatorBlock';
export { default as SpacerBlock } from './SpacerBlock';
export { default as QuoteBlock } from './QuoteBlock';
export { default as ButtonBlock } from './ButtonBlock';
export { default as ListBlock } from './ListBlock';
export { default as CodeBlock } from './CodeBlock';

// Block 组件映射表
export const blockComponents: Record<string, React.ComponentType<any>> = {
    paragraph: require('./ParagraphBlock').default,
    heading: require('./HeadingBlock').default,
    separator: require('./SeparatorBlock').default,
    spacer: require('./SpacerBlock').default,
    quote: require('./QuoteBlock').default,
    button: require('./ButtonBlock').default,
    list: require('./ListBlock').default,
    code: require('./CodeBlock').default,
};
