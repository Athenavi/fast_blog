'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Textarea} from '@/components/ui/textarea';
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from '@/components/ui/table';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue,} from "@/components/ui/select";
import {Edit, Plus, Save, Trash2} from 'lucide-react';
import {useToast} from '@/hooks/use-toast';

interface Page {
    id: number;
    title: string;
    slug: string;
    excerpt?: string;
    status: number;
    parent_id?: number;
    order_index: number;
    created_at?: string;
    updated_at?: string;
}

export default function PagesManagement() {
    const [pages, setPages] = useState<Page[]>([]);
    const [loading, setLoading] = useState(true);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingPage, setEditingPage] = useState<Page | null>(null);
    const {toast} = useToast();

    const [formData, setFormData] = useState({
        title: '',
        slug: '',
        content: '',
        excerpt: '',
        status: 0,
        parent_id: null as number | null,
        order_index: 0,
        meta_title: '',
        meta_description: '',
        meta_keywords: ''
    });

    useEffect(() => {
        fetchPages();
    }, []);

    const fetchPages = async () => {
        try {
            setLoading(true);
            const response = await fetch('/api/v1/pages?page=1&per_page=100');
            const data = await response.json();

            if (data.success) {
                setPages(data.data.pages || []);
            } else {
                toast({
                    title: '获取页面列表失败',
                    description: data.error,
                    variant: 'destructive'
                });
            }
        } catch (error) {
            toast({
                title: '网络错误',
                description: '无法连接到服务器',
                variant: 'destructive'
            });
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        try {
            const method = editingPage ? 'PUT' : 'POST';
            const url = editingPage ? `/api/v1/pages/${editingPage.id}` : '/api/v1/pages';

            const formDataObj = new FormData();
            Object.entries(formData).forEach(([key, value]) => {
                if (value !== null && value !== undefined && value !== '') {
                    formDataObj.append(key, value.toString());
                }
            });

            const response = await fetch(url, {
                method,
                body: formDataObj
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: editingPage ? '页面更新成功' : '页面创建成功',
                    description: data.data.message
                });
                setDialogOpen(false);
                resetForm();
                fetchPages();
            } else {
                toast({
                    title: '操作失败',
                    description: data.error,
                    variant: 'destructive'
                });
            }
        } catch (error) {
            toast({
                title: '网络错误',
                description: '无法连接到服务器',
                variant: 'destructive'
            });
        }
    };

    const handleDelete = async (pageId: number) => {
        if (!confirm('确定要删除这个页面吗？')) return;

        try {
            const response = await fetch(`/api/v1/pages/${pageId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '删除成功',
                    description: data.data.message
                });
                fetchPages();
            } else {
                toast({
                    title: '删除失败',
                    description: data.error,
                    variant: 'destructive'
                });
            }
        } catch (error) {
            toast({
                title: '网络错误',
                description: '无法连接到服务器',
                variant: 'destructive'
            });
        }
    };

    const handleEdit = (page: Page) => {
        setEditingPage(page);
        setFormData({
            title: page.title,
            slug: page.slug,
            content: '',
            excerpt: page.excerpt || '',
            status: page.status,
            parent_id: page.parent_id || null,
            order_index: page.order_index,
            meta_title: '',
            meta_description: '',
            meta_keywords: ''
        });
        setDialogOpen(true);
    };

    const resetForm = () => {
        setEditingPage(null);
        setFormData({
            title: '',
            slug: '',
            content: '',
            excerpt: '',
            status: 0,
            parent_id: null,
            order_index: 0,
            meta_title: '',
            meta_description: '',
            meta_keywords: ''
        });
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold">静态页面管理</h1>
                    <p className="text-muted-foreground mt-1">
                        管理网站的静态页面，如关于、联系我们等
                    </p>
                </div>

                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                    <DialogTrigger asChild>
                        <Button onClick={() => resetForm()}>
                            <Plus className="w-4 h-4 mr-2"/>
                            新建页面
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-2xl">
                        <DialogHeader>
                            <DialogTitle>{editingPage ? '编辑页面' : '新建页面'}</DialogTitle>
                            <DialogDescription>
                                {editingPage ? '修改页面信息' : '创建一个新的静态页面'}
                            </DialogDescription>
                        </DialogHeader>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="title">页面标题 *</Label>
                                    <Input
                                        id="title"
                                        value={formData.title}
                                        onChange={(e) => setFormData({...formData, title: e.target.value})}
                                        required
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="slug">Slug *</Label>
                                    <Input
                                        id="slug"
                                        value={formData.slug}
                                        onChange={(e) => setFormData({...formData, slug: e.target.value})}
                                        placeholder="about-us"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="excerpt">摘要</Label>
                                <Textarea
                                    id="excerpt"
                                    value={formData.excerpt}
                                    onChange={(e) => setFormData({...formData, excerpt: e.target.value})}
                                    rows={2}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="status">状态</Label>
                                    <Select
                                        value={formData.status.toString()}
                                        onValueChange={(value) => setFormData({...formData, status: parseInt(value)})}
                                    >
                                        <SelectTrigger>
                                            <SelectValue/>
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="0">草稿</SelectItem>
                                            <SelectItem value="1">已发布</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="order_index">排序</Label>
                                    <Input
                                        id="order_index"
                                        type="number"
                                        value={formData.order_index}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            order_index: parseInt(e.target.value)
                                        })}
                                    />
                                </div>
                            </div>

                            <DialogFooter>
                                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                                    取消
                                </Button>
                                <Button type="submit">
                                    <Save className="w-4 h-4 mr-2"/>
                                    保存
                                </Button>
                            </DialogFooter>
                        </form>
                    </DialogContent>
                </Dialog>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>页面列表</CardTitle>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="text-center py-8">加载中...</div>
                    ) : pages.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                            暂无页面，点击右上角创建新页面
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>标题</TableHead>
                                    <TableHead>Slug</TableHead>
                                    <TableHead>状态</TableHead>
                                    <TableHead>排序</TableHead>
                                    <TableHead>创建时间</TableHead>
                                    <TableHead className="text-right">操作</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {pages.map((page) => (
                                    <TableRow key={page.id}>
                                        <TableCell className="font-medium">{page.title}</TableCell>
                                        <TableCell>{page.slug}</TableCell>
                                        <TableCell>
                                            <Badge variant={page.status === 1 ? 'default' : 'secondary'}>
                                                {page.status === 1 ? '已发布' : '草稿'}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>{page.order_index}</TableCell>
                                        <TableCell>
                                            {page.created_at ? new Date(page.created_at).toLocaleDateString('zh-CN') : '-'}
                                        </TableCell>
                                        <TableCell className="text-right space-x-2">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => handleEdit(page)}
                                            >
                                                <Edit className="w-4 h-4"/>
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => handleDelete(page.id)}
                                                className="text-destructive hover:text-destructive"
                                            >
                                                <Trash2 className="w-4 h-4"/>
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
