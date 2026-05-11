/**
 * 表单构建器 - 可视化表单编辑器
 */

'use client';

import React, {useState} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Textarea} from '@/components/ui/textarea';
import {Switch} from '@/components/ui/switch';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import {
    Calendar,
    CheckSquare,
    Eye,
    FileText,
    Hash,
    List,
    Mail,
    MoveDown,
    MoveUp,
    Save,
    Settings,
    Trash2,
    Type
} from 'lucide-react';

interface FormField {
    id: string;
    label: string;
    field_type: string;
    placeholder?: string;
    required: boolean;
    options?: string[];
    help_text?: string;
}

interface Form {
    id?: number;
    title: string;
    slug: string;
    description: string;
    fields: FormField[];
    status: 'draft' | 'published';
}

const FormBuilder = () => {
    const [form, setForm] = useState<Form>({
        title: '',
        slug: '',
        description: '',
        fields: [],
        status: 'draft'
    });

    const [selectedField, setSelectedField] = useState<FormField | null>(null);
    const [fieldDialogOpen, setFieldDialogOpen] = useState(false);
    const [previewMode, setPreviewMode] = useState(false);

    // 字段类型选项
    const fieldTypes = [
        {value: 'text', label: '单行文本', icon: Type},
        {value: 'email', label: '邮箱', icon: Mail},
        {value: 'textarea', label: '多行文本', icon: FileText},
        {value: 'select', label: '下拉选择', icon: List},
        {value: 'checkbox', label: '复选框', icon: CheckSquare},
        {value: 'radio', label: '单选框', icon: CheckSquare},
        {value: 'number', label: '数字', icon: Hash},
        {value: 'date', label: '日期', icon: Calendar}
    ];

    // 添加字段
    const handleAddField = (fieldType: string) => {
        const newField: FormField = {
            id: `field_${Date.now()}`,
            label: `新字段`,
            field_type: fieldType,
            placeholder: '',
            required: false,
            options: fieldType === 'select' || fieldType === 'radio' ? ['选项1', '选项2'] : undefined,
            help_text: ''
        };

        setForm(prev => ({
            ...prev,
            fields: [...prev.fields, newField]
        }));
    };

    // 删除字段
    const handleDeleteField = (fieldId: string) => {
        setForm(prev => ({
            ...prev,
            fields: prev.fields.filter(f => f.id !== fieldId)
        }));
    };

    // 移动字段
    const handleMoveField = (index: number, direction: 'up' | 'down') => {
        const newFields = [...form.fields];
        const newIndex = direction === 'up' ? index - 1 : index + 1;

        if (newIndex < 0 || newIndex >= newFields.length) return;

        [newFields[index], newFields[newIndex]] = [newFields[newIndex], newFields[index]];

        setForm(prev => ({
            ...prev,
            fields: newFields
        }));
    };

    // 编辑字段
    const handleEditField = (field: FormField) => {
        setSelectedField({...field});
        setFieldDialogOpen(true);
    };

    // 保存字段编辑
    const handleSaveField = () => {
        if (!selectedField) return;

        setForm(prev => ({
            ...prev,
            fields: prev.fields.map(f =>
                f.id === selectedField.id ? selectedField : f
            )
        }));

        setFieldDialogOpen(false);
        setSelectedField(null);
    };

    // 自动生成slug
    const generateSlug = (title: string) => {
        return title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    };

    // 渲染预览
    const renderPreview = () => {
        return (
            <div className="space-y-4">
                {form.fields.map((field) => (
                    <div key={field.id} className="space-y-2">
                        <Label>
                            {field.label}
                            {field.required && <span className="text-red-500 ml-1">*</span>}
                        </Label>

                        {field.field_type === 'text' && (
                            <Input placeholder={field.placeholder} disabled/>
                        )}

                        {field.field_type === 'email' && (
                            <Input type="email" placeholder={field.placeholder} disabled/>
                        )}

                        {field.field_type === 'textarea' && (
                            <Textarea placeholder={field.placeholder} disabled/>
                        )}

                        {field.field_type === 'number' && (
                            <Input type="number" placeholder={field.placeholder} disabled/>
                        )}

                        {field.field_type === 'date' && (
                            <Input type="date" disabled/>
                        )}

                        {field.field_type === 'select' && field.options && (
                            <Select disabled>
                                <SelectTrigger>
                                    <SelectValue placeholder="请选择"/>
                                </SelectTrigger>
                                <SelectContent>
                                    {field.options.map((opt, idx) => (
                                        <SelectItem key={idx} value={opt}>{opt}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        )}

                        {field.field_type === 'checkbox' && field.options && (
                            <div className="space-y-2">
                                {field.options.map((opt, idx) => (
                                    <div key={idx} className="flex items-center gap-2">
                                        <input type="checkbox" disabled/>
                                        <Label>{opt}</Label>
                                    </div>
                                ))}
                            </div>
                        )}

                        {field.field_type === 'radio' && field.options && (
                            <div className="space-y-2">
                                {field.options.map((opt, idx) => (
                                    <div key={idx} className="flex items-center gap-2">
                                        <input type="radio" name={field.id} disabled/>
                                        <Label>{opt}</Label>
                                    </div>
                                ))}
                            </div>
                        )}

                        {field.help_text && (
                            <p className="text-xs text-gray-500">{field.help_text}</p>
                        )}
                    </div>
                ))}

                <Button className="w-full" disabled>提交</Button>
            </div>
        );
    };

    return (
        <div className="space-y-6">
            {/* 页面标题 */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">表单构建器</h1>
                    <p className="text-gray-600 dark:text-gray-400 mt-1">
                        拖拽式表单编辑器，轻松创建自定义表单
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button
                        variant="outline"
                        onClick={() => setPreviewMode(!previewMode)}
                    >
                        <Eye className="w-4 h-4 mr-2"/>
                        {previewMode ? '编辑模式' : '预览'}
                    </Button>
                    <Button>
                        <Save className="w-4 h-4 mr-2"/>
                        保存表单
                    </Button>
                </div>
            </div>

            {!previewMode ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* 左侧：字段工具栏 */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg">添加字段</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-2 gap-2">
                                {fieldTypes.map((type) => {
                                    const Icon = type.icon;
                                    return (
                                        <Button
                                            key={type.value}
                                            variant="outline"
                                            className="h-auto py-3 flex flex-col gap-2"
                                            onClick={() => handleAddField(type.value)}
                                        >
                                            <Icon className="w-5 h-5"/>
                                            <span className="text-xs">{type.label}</span>
                                        </Button>
                                    );
                                })}
                            </div>
                        </CardContent>
                    </Card>

                    {/* 中间：表单编辑区 */}
                    <Card className="lg:col-span-2">
                        <CardHeader>
                            <CardTitle className="text-lg">表单配置</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {/* 基本信息 */}
                            <div className="space-y-3">
                                <div>
                                    <Label htmlFor="form-title">表单标题</Label>
                                    <Input
                                        id="form-title"
                                        value={form.title}
                                        onChange={(e) => setForm({
                                            ...form,
                                            title: e.target.value,
                                            slug: generateSlug(e.target.value)
                                        })}
                                        placeholder="输入表单标题"
                                    />
                                </div>

                                <div>
                                    <Label htmlFor="form-slug">表单标识</Label>
                                    <Input
                                        id="form-slug"
                                        value={form.slug}
                                        onChange={(e) => setForm({...form, slug: e.target.value})}
                                        placeholder="form-slug"
                                    />
                                </div>

                                <div>
                                    <Label htmlFor="form-description">表单描述</Label>
                                    <Textarea
                                        id="form-description"
                                        value={form.description}
                                        onChange={(e) => setForm({...form, description: e.target.value})}
                                        placeholder="描述此表单的用途"
                                        rows={3}
                                    />
                                </div>
                            </div>

                            {/* 字段列表 */}
                            <div className="border-t pt-4">
                                <h3 className="font-medium mb-3">表单字段 ({form.fields.length})</h3>

                                {form.fields.length === 0 ? (
                                    <div className="text-center py-8 text-gray-500 border-2 border-dashed rounded-lg">
                                        <p>点击左侧按钮添加字段</p>
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        {form.fields.map((field, index) => (
                                            <div
                                                key={field.id}
                                                className="flex items-center gap-3 p-3 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                                            >
                                                <div className="flex-1">
                                                    <div className="font-medium text-sm">{field.label}</div>
                                                    <div className="text-xs text-gray-500">
                                                        {fieldTypes.find(t => t.value === field.field_type)?.label}
                                                        {field.required && ' • 必填'}
                                                    </div>
                                                </div>

                                                <div className="flex items-center gap-1">
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        onClick={() => handleMoveField(index, 'up')}
                                                        disabled={index === 0}
                                                    >
                                                        <MoveUp className="w-4 h-4"/>
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        onClick={() => handleMoveField(index, 'down')}
                                                        disabled={index === form.fields.length - 1}
                                                    >
                                                        <MoveDown className="w-4 h-4"/>
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        onClick={() => handleEditField(field)}
                                                    >
                                                        <Settings className="w-4 h-4"/>
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        onClick={() => handleDeleteField(field.id)}
                                                        className="text-red-600"
                                                    >
                                                        <Trash2 className="w-4 h-4"/>
                                                    </Button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            ) : (
                /* 预览模式 */
                <Card>
                    <CardHeader>
                        <CardTitle>{form.title || '未命名表单'}</CardTitle>
                        {form.description && (
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                {form.description}
                            </p>
                        )}
                    </CardHeader>
                    <CardContent>
                        {form.fields.length === 0 ? (
                            <div className="text-center py-8 text-gray-500">
                                <p>暂无字段，请返回编辑模式添加</p>
                            </div>
                        ) : (
                            renderPreview()
                        )}
                    </CardContent>
                </Card>
            )}

            {/* 字段编辑对话框 */}
            <Dialog open={fieldDialogOpen} onOpenChange={setFieldDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>编辑字段</DialogTitle>
                    </DialogHeader>

                    {selectedField && (
                        <div className="space-y-4 py-4">
                            <div>
                                <Label htmlFor="field-label">字段标签</Label>
                                <Input
                                    id="field-label"
                                    value={selectedField.label}
                                    onChange={(e) => setSelectedField({
                                        ...selectedField,
                                        label: e.target.value
                                    })}
                                />
                            </div>

                            <div>
                                <Label htmlFor="field-placeholder">占位符</Label>
                                <Input
                                    id="field-placeholder"
                                    value={selectedField.placeholder || ''}
                                    onChange={(e) => setSelectedField({
                                        ...selectedField,
                                        placeholder: e.target.value
                                    })}
                                />
                            </div>

                            <div>
                                <Label htmlFor="field-help">帮助文本</Label>
                                <Input
                                    id="field-help"
                                    value={selectedField.help_text || ''}
                                    onChange={(e) => setSelectedField({
                                        ...selectedField,
                                        help_text: e.target.value
                                    })}
                                />
                            </div>

                            {(selectedField.field_type === 'select' ||
                                selectedField.field_type === 'checkbox' ||
                                selectedField.field_type === 'radio') && (
                                <div>
                                    <Label>选项（每行一个）</Label>
                                    <Textarea
                                        value={selectedField.options?.join('\n') || ''}
                                        onChange={(e) => setSelectedField({
                                            ...selectedField,
                                            options: e.target.value.split('\n').filter(Boolean)
                                        })}
                                        rows={4}
                                        placeholder="选项1&#10;选项2&#10;选项3"
                                    />
                                </div>
                            )}

                            <div className="flex items-center justify-between">
                                <Label htmlFor="field-required">必填字段</Label>
                                <Switch
                                    id="field-required"
                                    checked={selectedField.required}
                                    onCheckedChange={(checked) => setSelectedField({
                                        ...selectedField,
                                        required: checked
                                    })}
                                />
                            </div>
                        </div>
                    )}

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setFieldDialogOpen(false)}>
                            取消
                        </Button>
                        <Button onClick={handleSaveField}>
                            保存
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default FormBuilder;
