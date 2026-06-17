/**
 * BlockPreview — 按块类型实时渲染可视化预览
 *
 * 与 BlockFieldEditor 的数据结构一一对应，
 * 将 block.data 渲染为其视觉形态。
 */
import React from 'react';

interface Props {
    type: string;
    data: Record<string, any>;
    styles?: Record<string, any>;
}

// ── 基础样式包装 ──

const Container = ({children, styles = {}, className = ''}: {
    children: React.ReactNode;
    styles?: Record<string, any>;
    className?: string;
}) => {
    const s: Record<string, string> = {};
    if (styles.backgroundColor) s.backgroundColor = styles.backgroundColor;
    if (styles.color) s.color = styles.color;
    if (styles.padding) s.padding = `${styles.padding}px`;
    if (styles.margin) s.margin = `${styles.margin}px`;
    if (styles.borderRadius) s.borderRadius = `${styles.borderRadius}px`;
    return <div style={s} className={`${className}`}>{children}</div>;
};

// ── 各块类型预览 ──

const TextPreview = ({data}: { data: Record<string, any> }) => (
    <p className="text-gray-800 dark:text-gray-200 leading-relaxed"
       style={{fontSize: data.fontSize ? `${data.fontSize}px` : undefined, lineHeight: data.lineHeight}}>
        {data.content || data.text || '(空文本)'}
    </p>
);

const ImagePreview = ({data}: { data: Record<string, any> }) => (
    <div className="text-center">
        {data.src ? (
            <img src={data.src} alt={data.alt || ''}
                 className="max-w-full h-auto rounded-lg mx-auto shadow-sm"
                 style={{borderRadius: data.borderRadius ? `${data.borderRadius}px` : undefined}}
                 onError={(e) => {
                     (e.target as HTMLImageElement).style.display = 'none';
                     (e.target as HTMLImageElement).nextElementSibling?.classList.remove('hidden');
                 }}/>
        ) : null}
        <div className={`${data.src ? 'hidden' : ''} p-8 bg-gray-100 dark:bg-gray-800 rounded-lg text-gray-400`}>
            🖼️ {data.alt || '图片'}
        </div>
        {data.caption && <p className="text-xs text-gray-400 mt-1">{data.caption}</p>}
    </div>
);

const VideoPreview = ({data}: { data: Record<string, any> }) => (
    <div className="aspect-video bg-gray-900 rounded-lg flex items-center justify-center text-white">
        {data.url ? (
            <div className="text-center">
                <div className="text-4xl mb-2">▶️</div>
                <p className="text-sm opacity-80">{data.title || '视频'}</p>
            </div>
        ) : (
            <div className="text-center text-gray-400">
                <div className="text-4xl mb-2">🎬</div>
                <p className="text-sm">视频</p>
            </div>
        )}
    </div>
);

const ButtonPreview = ({data}: { data: Record<string, any> }) => {
    const variant = data.style || 'primary';
    const base = 'inline-block px-6 py-2.5 rounded-lg text-sm font-medium transition cursor-default';
    const styles: Record<string, string> = {
        primary: 'bg-blue-600 text-white shadow-sm',
        secondary: 'bg-gray-600 text-white',
        outline: 'border-2 border-blue-600 text-blue-600 bg-transparent',
    };
    return (
        <div className="text-center">
            <span className={`${base} ${styles[variant] || styles.primary}`}>
                {data.text || '按钮'}
            </span>
        </div>
    );
};

const QuotePreview = ({data}: { data: Record<string, any> }) => (
    <blockquote className="border-l-4 border-blue-400 pl-4 py-2 italic text-gray-600 dark:text-gray-300">
        <p className="text-sm">{data.text || '(引用内容)'}</p>
        {data.author && <footer className="text-xs text-gray-400 mt-1 not-italic">— {data.author}</footer>}
    </blockquote>
);

const CodePreview = ({data}: { data: Record<string, any> }) => (
    <pre className="bg-gray-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto font-mono">
        <div className="text-gray-500 text-[10px] mb-2 uppercase">{data.language || 'code'}</div>
        <code>{data.code || '// 代码块'}</code>
    </pre>
);

const ProgressPreview = ({data}: { data: Record<string, any> }) => {
    const val = Math.min(100, Math.max(0, Number(data.value) || 0));
    return (
        <div className="space-y-1">
            <div className="flex justify-between text-xs text-gray-500">
                <span>{data.label || '进度'}</span>
                <span>{val}%</span>
            </div>
            <div className="w-full h-2.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full transition-all duration-300"
                     style={{width: `${val}%`}}/>
            </div>
        </div>
    );
};

const DividerPreview = () => (
    <hr className="border-t border-gray-200 dark:border-gray-700 my-4"/>
);

const HeroPreview = ({data}: { data: Record<string, any> }) => {
    const bg = data.bgColor || '#f8fafc';
    return (
        <div className="text-center py-8 px-6 rounded-lg" style={{backgroundColor: bg}}>
            {data.title && <h2 className="text-2xl font-bold mb-2">{data.title}</h2>}
            {data.subtitle && <p className="text-sm opacity-80 mb-4">{data.subtitle}</p>}
            {data.cta_text && (
                <span className="inline-block px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium shadow-sm">
                    {data.cta_text}
                </span>
            )}
        </div>
    );
};

const CtaPreview = ({data}: { data: Record<string, any> }) => {
    const bg = data.bgColor || '#1e40af';
    const textColor = data.textColor || '#ffffff';
    return (
        <div className="text-center py-8 px-6 rounded-lg" style={{backgroundColor: bg, color: textColor}}>
            {data.title && <h2 className="text-xl font-bold mb-1">{data.title}</h2>}
            {data.subtitle && <p className="text-sm opacity-90 mb-4">{data.subtitle}</p>}
            {data.button_text && (
                <span className="inline-block px-6 py-2.5 bg-white text-gray-900 rounded-lg text-sm font-medium shadow-sm">
                    {data.button_text}
                </span>
            )}
        </div>
    );
};

const GridPreview = ({data}: { data: Record<string, any> }) => (
    <div className="space-y-3">
        {data.title && <h3 className="text-base font-semibold text-center">{data.title}</h3>}
        <div className="grid grid-cols-2 gap-3">
            {(data.features || []).map((f: any, i: number) => (
                <div key={i} className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 text-center">
                    <div className="text-xl mb-1">⭐</div>
                    <div className="text-sm font-medium">{f.title}</div>
                    <div className="text-[11px] text-gray-400 mt-0.5">{f.desc}</div>
                </div>
            ))}
        </div>
    </div>
);

const TeamPreview = ({data}: { data: Record<string, any> }) => (
    <div className="space-y-3">
        {data.title && <h3 className="text-base font-semibold text-center">{data.title}</h3>}
        <div className="grid grid-cols-2 gap-3">
            {(data.members || []).map((m: any, i: number) => (
                <div key={i} className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 text-center">
                    <div className="w-12 h-12 mx-auto rounded-full bg-gray-200 dark:bg-gray-700 mb-2"/>
                    <div className="text-sm font-medium">{m.name}</div>
                    <div className="text-[11px] text-gray-400">{m.role}</div>
                </div>
            ))}
        </div>
    </div>
);

const PricingPreview = ({data}: { data: Record<string, any> }) => (
    <div className="space-y-3">
        {data.title && <h3 className="text-base font-semibold text-center">{data.title}</h3>}
        <div className="grid grid-cols-2 gap-3">
            {(data.plans || []).map((p: any, i: number) => (
                <div key={i}
                     className={`p-3 rounded-lg border text-center ${p.highlighted ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 shadow-md' : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'}`}>
                    <div className="text-sm font-medium">{p.name}</div>
                    <div className="text-lg font-bold mt-1">{p.price}</div>
                    <div className="text-[10px] text-gray-400 mt-1">{(p.features || []).length} 项功能</div>
                </div>
            ))}
        </div>
    </div>
);

const FaqPreview = ({data}: { data: Record<string, any> }) => (
    <div className="space-y-2">
        {data.title && <h3 className="text-base font-semibold text-center mb-2">{data.title}</h3>}
        {(data.faqs || []).map((f: any, i: number) => (
            <details key={i} className="border border-gray-200 dark:border-gray-700 rounded-lg">
                <summary className="px-3 py-2 text-sm font-medium cursor-pointer">{f.question}</summary>
                <p className="px-3 pb-2 text-xs text-gray-500">{f.answer}</p>
            </details>
        ))}
    </div>
);

const TestimonialPreview = ({data}: { data: Record<string, any> }) => (
    <div className="space-y-3">
        {data.title && <h3 className="text-base font-semibold text-center">{data.title}</h3>}
        <div className="grid grid-cols-2 gap-3">
            {(data.testimonials || []).map((t: any, i: number) => (
                <div key={i} className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700">
                    <p className="text-xs italic text-gray-600 dark:text-gray-300">"{t.quote}"</p>
                    <div className="mt-2 text-[11px] font-medium">{t.name}</div>
                    {t.role && <div className="text-[10px] text-gray-400">{t.role}</div>}
                </div>
            ))}
        </div>
    </div>
);

const FormPreview = ({data}: { data: Record<string, any> }) => (
    <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg text-center">
        {data.title && <h3 className="text-sm font-semibold mb-1">{data.title}</h3>}
        {data.subtitle && <p className="text-xs text-gray-400 mb-3">{data.subtitle}</p>}
        <div className="space-y-2 max-w-xs mx-auto">
            {(data.fields || []).map((f: any, i: number) => (
                <div key={i} className="h-8 bg-white dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600 flex items-center px-3">
                    <span className="text-xs text-gray-400">{f.name || '字段'}</span>
                </div>
            ))}
            <div className="h-8 bg-blue-600 rounded flex items-center justify-center text-white text-xs font-medium">
                提交
            </div>
        </div>
    </div>
);

const NewsletterPreview = ({data}: { data: Record<string, any> }) => (
    <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg text-center">
        <div className="flex gap-2 max-w-xs mx-auto">
            <div className="flex-1 h-8 bg-white dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600 flex items-center px-3">
                <span className="text-xs text-gray-400">{data.placeholder || '输入邮箱'}</span>
            </div>
            <div className="px-4 h-8 bg-blue-600 rounded flex items-center text-white text-xs font-medium">
                {data.buttonText || '订阅'}
            </div>
        </div>
    </div>
);

const StatsPreview = ({data}: { data: Record<string, any> }) => (
    <div className="grid grid-cols-2 gap-3">
        {(data.items || []).map((s: any, i: number) => (
            <div key={i} className="text-center p-3">
                <div className="text-2xl font-bold text-blue-600">{s.value || '—'}</div>
                <div className="text-xs text-gray-500">{s.label}</div>
            </div>
        ))}
    </div>
);

const IconListPreview = ({data}: { data: Record<string, any> }) => (
    <div className="space-y-2">
        {(data.items || []).map((item: any, i: number) => (
            <div key={i} className="flex items-start gap-3 p-2">
                <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 shrink-0">
                    ⭐
                </div>
                <div>
                    <div className="text-sm font-medium">{item.title}</div>
                    {item.desc && <div className="text-xs text-gray-400">{item.desc}</div>}
                </div>
            </div>
        ))}
    </div>
);

const ColumnContainerPreview = ({data}: { data: Record<string, any> }) => (
    <div className="grid grid-cols-2 gap-3">
        {Array.from({length: Math.min(data.columns || 2, 6)}).map((_, i) => (
            <div key={i} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-dashed border-gray-200 dark:border-gray-700 text-center text-xs text-gray-400">
                列 {i + 1}
            </div>
        ))}
    </div>
);

const HeadingPreview = ({data}: { data: Record<string, any> }) => {
    const lvl = Math.min(Math.max(Number(data.level) || 2, 1), 6);
    const size = [undefined, 'text-3xl', 'text-2xl', 'text-xl', 'text-lg', 'text-base', 'text-sm'][lvl];
    const align = data.align === 'center' ? 'text-center' : data.align === 'right' ? 'text-right' : 'text-left';
    return <div className={`${size} font-bold ${align}`}>{data.text || '标题'}</div>;
};

const EmptyPreview = (_data: Record<string, any>) => (
    <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg text-center text-xs text-gray-400">
        该组件无需配置（或将显示自定义内容）
    </div>
);

// ── 预览注册表 ──

const PREVIEW_MAP: Record<string, React.FC<{ data: Record<string, any> }>> = {
    text: TextPreview,
    paragraph: TextPreview,
    image: ImagePreview,
    video: VideoPreview,
    button: ButtonPreview,
    quote: QuotePreview,
    code: CodePreview,
    progress: ProgressPreview,
    divider: DividerPreview,
    newsletter: NewsletterPreview,
    'hero-section': HeroPreview,
    hero: HeroPreview,
    'cta-section': CtaPreview,
    cta: CtaPreview,
    'features-grid': GridPreview,
    grid: GridPreview,
    'team-members': TeamPreview,
    team: TeamPreview,
    'pricing-table': PricingPreview,
    pricing: PricingPreview,
    'contact-form': FormPreview,
    form: FormPreview,
    testimonials: TestimonialPreview,
    testimonial: TestimonialPreview,
    'faq-section': FaqPreview,
    faq: FaqPreview,
    'icon-list': IconListPreview,
    columns: ColumnContainerPreview,
    'column-container': ColumnContainerPreview,
    heading: HeadingPreview,
    stats: StatsPreview,
    'stats-counter': StatsPreview,
    'column': EmptyPreview,
};

export default function BlockPreview({type, data = {}, styles = {}}: Props) {
    const Preview = PREVIEW_MAP[type];
    return (
        <Container styles={styles}>
            {Preview ? (
                <Preview data={data}/>
            ) : (
                <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg text-center text-xs text-gray-400">
                    {type}（暂无可视预览）
                </div>
            )}
        </Container>
    );
}
