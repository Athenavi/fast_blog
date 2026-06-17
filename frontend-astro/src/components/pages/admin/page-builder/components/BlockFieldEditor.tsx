/**
 * BlockFieldEditor — 按块类型分派到专用编辑器
 *
 * 不再使用内联函数创建 JSX，而是定义组件化的字段编辑器。
 * 每个块类型有独立的编辑器组件，方便扩展和维护。
 */
import React from 'react';

interface Props {
    type: string;
    data: Record<string, any>;
    onChange: (data: Record<string, any>) => void;
}

// ── 基础字段组件 ──

const Field = ({label, children}: { label: string; children: React.ReactNode }) => (
    <div className="mb-2">
        <label className="block text-[11px] text-gray-400 mb-1">{label}</label>
        {children}
    </div>
);

const TextInput = ({value, onChange, placeholder}: {
    value?: string;
    onChange: (v: string) => void;
    placeholder?: string;
}) => (
    <input type="text" value={value ?? ''} onChange={e => onChange(e.target.value)}
           placeholder={placeholder}
           className="w-full px-2.5 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"/>
);

const TextArea = ({value, onChange, rows = 3}: {
    value?: string;
    onChange: (v: string) => void;
    rows?: number;
}) => (
    <textarea value={value ?? ''} onChange={e => onChange(e.target.value)} rows={rows}
              className="w-full px-2.5 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"/>
);

const NumberInput = ({value, onChange, min, max}: {
    value?: number;
    onChange: (v: number) => void;
    min?: number;
    max?: number;
}) => (
    <input type="number" value={value ?? 0} onChange={e => onChange(Number(e.target.value))}
           min={min} max={max}
           className="w-full px-2.5 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"/>
);

const ColorInput = ({value, onChange}: { value?: string; onChange: (v: string) => void }) => (
    <div className="flex items-center gap-2">
        <input type="color" value={value || '#ffffff'}
               onChange={e => onChange(e.target.value)}
               className="w-8 h-8 rounded cursor-pointer border border-gray-200 dark:border-gray-700"/>
        <input type="text" value={value || '#ffffff'}
               onChange={e => onChange(e.target.value)}
               className="flex-1 px-2.5 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"/>
    </div>
);

const SelectInput = ({value, onChange, options}: {
    value?: string;
    onChange: (v: string) => void;
    options: { label: string; value: string }[];
}) => (
    <select value={value ?? options[0]?.value ?? ''} onChange={e => onChange(e.target.value)}
            className="w-full px-2.5 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500">
        {options.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
    </select>
);

/** 列表编辑器（用于 features / team / plans / faqs 等数组数据） */
const ListEditor = ({items = [], fields, defaultItem, setKey, onChange}: {
    items?: any[];
    fields: { key: string; label: string }[];
    defaultItem: Record<string, any>;
    setKey: string;
    onChange: (key: string, val: any[]) => void;
}) => (
    <Field label={setKey}>
        <div className="space-y-1.5">
            {items.map((item, i) => (
                <div key={i} className="flex items-center gap-1.5">
                    {fields.map(f => (
                        <input key={f.key} type="text" value={item[f.key] ?? ''}
                               onChange={e => {
                                   const next = [...items];
                                   next[i] = {...next[i], [f.key]: e.target.value};
                                   onChange(setKey, next);
                               }}
                               placeholder={f.label}
                               className="flex-1 px-1.5 py-1 border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-[11px] focus:outline-none focus:ring-1 focus:ring-blue-500"/>
                    ))}
                    <button onClick={() => onChange(setKey, items.filter((_, j) => j !== i))}
                            className="p-0.5 text-red-400 hover:text-red-600 text-sm">&times;</button>
                </div>
            ))}
            <button onClick={() => onChange(setKey, [...items, {...defaultItem}])}
                    className="text-[11px] text-blue-500 hover:text-blue-700">
                + 添加
            </button>
        </div>
    </Field>
);

// ── 各类型编辑器 ──

const TextEditor = ({data, onChange}: {
    data: Record<string, any>;
    onChange: (d: Record<string, any>) => void;
}) => (
    <Field label="文本内容">
        <TextArea value={data.content} onChange={v => onChange({...data, content: v})}/>
    </Field>
);

const ImageEditor = ({data, onChange}: {
    data: Record<string, any>;
    onChange: (d: Record<string, any>) => void;
}) => (
    <>
        <Field label="图片 URL"><TextInput value={data.src} onChange={v => onChange({...data, src: v})}
                                           placeholder="https://..."/></Field>
        <Field label="描述"><TextInput value={data.alt} onChange={v => onChange({...data, alt: v})}/></Field>
    </>
);

const VideoEditor = ({data, onChange}: {
    data: Record<string, any>;
    onChange: (d: Record<string, any>) => void;
}) => (
    <>
        <Field label="视频 URL"><TextInput value={data.url} onChange={v => onChange({...data, url: v})}/></Field>
        <Field label="标题"><TextInput value={data.title} onChange={v => onChange({...data, title: v})}/></Field>
    </>
);

const ButtonEditor = ({data, onChange}: {
    data: Record<string, any>;
    onChange: (d: Record<string, any>) => void;
}) => (
    <>
        <Field label="按钮文字"><TextInput value={data.text} onChange={v => onChange({...data, text: v})}/></Field>
        <Field label="链接"><TextInput value={data.url} onChange={v => onChange({...data, url: v})}/></Field>
        <Field label="样式">
            <SelectInput value={data.style ?? 'primary'} onChange={v => onChange({...data, style: v})}
                         options={[{label: '主要', value: 'primary'}, {label: '次要', value: 'secondary'}, {
                             label: '边框',
                             value: 'outline'
                         }]}/>
        </Field>
    </>
);

const HeroEditor = ({data, onChange}: {
    data: Record<string, any>;
    onChange: (d: Record<string, any>) => void;
}) => (
    <>
        <Field label="标题"><TextInput value={data.title} onChange={v => onChange({...data, title: v})}/></Field>
        <Field label="副标题"><TextInput value={data.subtitle} onChange={v => onChange({...data, subtitle: v})}/></Field>
        <Field label="背景色"><ColorInput value={data.bgColor}
                                          onChange={v => onChange({...data, bgColor: v})}/></Field>
        <Field label="图片 URL"><TextInput value={data.imageUrl} onChange={v => onChange({...data, imageUrl: v})}
                                           placeholder="https://..."/></Field>
        <Field label="按钮文字"><TextInput value={data.cta_text}
                                          onChange={v => onChange({...data, cta_text: v})}/></Field>
        <Field label="按钮链接"><TextInput value={data.cta_link}
                                          onChange={v => onChange({...data, cta_link: v})}/></Field>
    </>
);

const CtaEditor = ({data, onChange}: {
    data: Record<string, any>;
    onChange: (d: Record<string, any>) => void;
}) => (
    <>
        <Field label="标题"><TextInput value={data.title} onChange={v => onChange({...data, title: v})}/></Field>
        <Field label="副标题"><TextInput value={data.subtitle} onChange={v => onChange({...data, subtitle: v})}/></Field>
        <Field label="背景色"><ColorInput value={data.bgColor}
                                          onChange={v => onChange({...data, bgColor: v})}/></Field>
        <Field label="按钮文字"><TextInput value={data.button_text}
                                          onChange={v => onChange({...data, button_text: v})}/></Field>
        <Field label="按钮链接"><TextInput value={data.button_link}
                                          onChange={v => onChange({...data, button_link: v})}/></Field>
    </>
);

const GridEditor = ({data, onChange}: {
    data: Record<string, any>;
    onChange: (d: Record<string, any>) => void;
}) => (
    <>
        <Field label="区块标题"><TextInput value={data.title} onChange={v => onChange({...data, title: v})}/></Field>
        <ListEditor items={data.features} setKey="features"
                    fields={[{key: 'icon', label: '图标'}, {key: 'title', label: '标题'}, {
                        key: 'desc',
                        label: '描述'
                    }]}
                    defaultItem={{icon: 'star', title: '', desc: ''}}
                    onChange={(k, v) => onChange({...data, [k]: v})}/>
    </>
);

const DefaultEditor = ({data, onChange}: {
    data: Record<string, any>;
    onChange: (d: Record<string, any>) => void;
}) => (
    <Field label="原始数据">
        <textarea value={JSON.stringify(data, null, 2)}
                  onChange={e => {
                      try {
                          onChange(JSON.parse(e.target.value));
                      } catch {
                          // ignore invalid JSON
                      }
                  }}
                  rows={4}
                  className="w-full px-2.5 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-[11px] font-mono focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"/>
    </Field>
);

// ── 编辑器注册表 ──

const EDITOR_MAP: Record<string, React.FC<{ data: Record<string, any>; onChange: (d: Record<string, any>) => void }>> = {
    text: TextEditor,
    image: ImageEditor,
    video: VideoEditor,
    button: ButtonEditor,
    quote: ({data, onChange}) => (
        <>
            <Field label="引用内容"><TextArea value={data.text}
                                              onChange={v => onChange({...data, text: v})}/></Field>
            <Field label="作者"><TextInput value={data.author} onChange={v => onChange({...data, author: v})}/></Field>
        </>
    ),
    code: ({data, onChange}) => (
        <>
            <Field label="语言">
                <SelectInput value={data.language} onChange={v => onChange({...data, language: v})}
                             options={[{label: 'JavaScript', value: 'js'}, {label: 'Python', value: 'python'}, {
                                 label: 'HTML',
                                 value: 'html'
                             }, {label: 'CSS', value: 'css'}, {label: 'Bash', value: 'bash'}]}/>
            </Field>
            <Field label="代码"><TextArea value={data.code} onChange={v => onChange({...data, code: v})} rows={5}/></Field>
        </>
    ),
    progress: ({data, onChange}) => (
        <>
            <Field label="百分比"><NumberInput value={data.value} onChange={v => onChange({...data, value: v})} min={0}
                                               max={100}/></Field>
            <Field label="标签"><TextInput value={data.label} onChange={v => onChange({...data, label: v})}/></Field>
        </>
    ),
    newsletter: ({data, onChange}) => (
        <>
            <Field label="占位文本"><TextInput value={data.placeholder}
                                               onChange={v => onChange({...data, placeholder: v})}/></Field>
            <Field label="按钮文字"><TextInput value={data.buttonText}
                                               onChange={v => onChange({...data, buttonText: v})}/></Field>
        </>
    ),
    divider: () => <p className="text-gray-400 text-[11px] py-2 text-center">分隔线（无可配置项）</p>,
    'hero-section': HeroEditor,
    hero: HeroEditor,
    'cta-section': CtaEditor,
    cta: CtaEditor,
    'features-grid': GridEditor,
    'grid': GridEditor,
    'team-members': ({data, onChange}) => (
        <>
            <Field label="区块标题"><TextInput value={data.title}
                                               onChange={v => onChange({...data, title: v})}/></Field>
            <ListEditor items={data.members} setKey="members"
                        fields={[{key: 'name', label: '姓名'}, {key: 'role', label: '职位'}]}
                        defaultItem={{name: '', role: ''}}
                        onChange={(k, v) => onChange({...data, [k]: v})}/>
        </>
    ),
    team: ({data, onChange}) => {
        const MembersEditor = EDITOR_MAP['team-members']!;
        return <MembersEditor data={data} onChange={onChange}/>;
    },
    'pricing-table': ({data, onChange}) => (
        <>
            <Field label="区块标题"><TextInput value={data.title}
                                               onChange={v => onChange({...data, title: v})}/></Field>
            <ListEditor items={data.plans} setKey="plans"
                        fields={[{key: 'name', label: '方案名'}, {key: 'price', label: '价格'}]}
                        defaultItem={{name: '', price: ''}}
                        onChange={(k, v) => onChange({...data, [k]: v})}/>
        </>
    ),
    pricing: ({data, onChange}) => {
        const PricingEditor = EDITOR_MAP['pricing-table']!;
        return <PricingEditor data={data} onChange={onChange}/>;
    },
    'contact-form': ({data, onChange}) => (
        <>
            <Field label="标题"><TextInput value={data.title} onChange={v => onChange({...data, title: v})}/></Field>
            <Field label="副标题"><TextInput value={data.subtitle}
                                             onChange={v => onChange({...data, subtitle: v})}/></Field>
            <ListEditor items={data.fields} setKey="fields"
                        fields={[{key: 'name', label: '字段名'}]}
                        defaultItem={{name: ''}}
                        onChange={(k, v) => onChange({...data, [k]: v})}/>
        </>
    ),
    form: ({data, onChange}) => {
        const FormEditor = EDITOR_MAP['contact-form']!;
        return <FormEditor data={data} onChange={onChange}/>;
    },
    testimonials: ({data, onChange}) => (
        <>
            <Field label="区块标题"><TextInput value={data.title}
                                               onChange={v => onChange({...data, title: v})}/></Field>
            <ListEditor items={data.testimonials} setKey="testimonials"
                        fields={[{key: 'quote', label: '评价'}, {key: 'name', label: '姓名'}, {
                            key: 'role',
                            label: '职位'
                        }]}
                        defaultItem={{quote: '', name: '', role: ''}}
                        onChange={(k, v) => onChange({...data, [k]: v})}/>
        </>
    ),
    testimonial: ({data, onChange}) => {
        const TestimonialsEditor = EDITOR_MAP.testimonials!;
        return <TestimonialsEditor data={data} onChange={onChange}/>;
    },
    'faq-section': ({data, onChange}) => (
        <>
            <Field label="区块标题"><TextInput value={data.title}
                                               onChange={v => onChange({...data, title: v})}/></Field>
            <ListEditor items={data.faqs} setKey="faqs"
                        fields={[{key: 'question', label: '问题'}, {key: 'answer', label: '答案'}]}
                        defaultItem={{question: '', answer: ''}}
                        onChange={(k, v) => onChange({...data, [k]: v})}/>
        </>
    ),
    faq: ({data, onChange}) => {
        const FaqEditor = EDITOR_MAP['faq-section']!;
        return <FaqEditor data={data} onChange={onChange}/>;
    },
    columns: ({data, onChange}) => (
        <>
            <Field label="列数"><NumberInput value={data.count} onChange={v => onChange({...data, count: v})} min={1}
                                             max={6}/></Field>
            <ListEditor items={data.content} setKey="content"
                        fields={[{key: 'content', label: '内容'}]}
                        defaultItem={{content: ''}}
                        onChange={(k, v) => onChange({...data, [k]: v})}/>
        </>
    ),
    'icon-list': ({data, onChange}) => (
        <ListEditor items={data.items} setKey="items"
                    fields={[{key: 'icon', label: '图标'}, {key: 'title', label: '标题'}, {
                        key: 'desc',
                        label: '描述'
                    }]}
                    defaultItem={{icon: 'star', title: '', desc: ''}}
                    onChange={(k, v) => onChange({...data, [k]: v})}/>
    ),
    stats: ({data, onChange}) => (
        <ListEditor items={data.items} setKey="items"
                    fields={[{key: 'value', label: '数值'}, {key: 'label', label: '标签'}]}
                    defaultItem={{value: '', label: ''}}
                    onChange={(k, v) => onChange({...data, [k]: v})}/>
    ),
    'stats-counter': ({data, onChange}) => {
        const StatsEditor = EDITOR_MAP.stats!;
        return <StatsEditor data={data} onChange={onChange}/>;
    },
};

// ── 主入口 ──

export default function BlockFieldEditor({type, data, onChange}: Props) {
    const Editor = EDITOR_MAP[type];
    if (Editor) {
        return <Editor data={data} onChange={onChange}/>;
    }
    return <DefaultEditor data={data} onChange={onChange}/>;
}
