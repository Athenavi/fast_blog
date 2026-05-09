'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Badge} from '@/components/ui/badge';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger
} from '@/components/ui/dialog';
import {useToast} from '@/hooks/use-toast';
import {Ad, AdSlot, AdvertisementService, RevenueReport} from '@/lib/api/advertisement-service';

export default function AdvertisementManagementPage() {
    const {toast} = useToast();
    const [slots, setSlots] = useState<AdSlot[]>([]);
    const [ads, setAds] = useState<Ad[]>([]);
    const [revenue, setRevenue] = useState<RevenueReport | null>(null);
    const [loading, setLoading] = useState(false);
    const [showCreateDialog, setShowCreateDialog] = useState(false);

    // 表单状态
    const [newAd, setNewAd] = useState({
        title: '',
        slot_id: '',
        ad_type: 'image',
        content: '',
        image_url: '',
        link_url: '',
        html_code: '',
        priority: 5,
        budget: undefined as number | undefined,
    });

    useEffect(() => {
        loadSlots();
        loadAds();
        loadRevenue();
    }, []);

    const loadSlots = async () => {
        try {
            const response = await AdvertisementService.getAdSlots();
            if (response.success && response.data) {
                setSlots(response.data.slots || []);
            }
        } catch (error) {
            console.error('Failed to load slots:', error);
        }
    };

    const loadAds = async () => {
        try {
            const response = await AdvertisementService.getAds();
            if (response.success && response.data) {
                setAds(response.data.ads || []);
            }
        } catch (error) {
            console.error('Failed to load ads:', error);
        }
    };

    const loadRevenue = async () => {
        try {
            const response = await AdvertisementService.getRevenueReport();
            if (response.success && response.data) {
                setRevenue(response.data);
            }
        } catch (error) {
            console.error('Failed to load revenue:', error);
        }
    };

    const handleCreateAd = async () => {
        if (!newAd.title || !newAd.slot_id) {
            toast({
                title: '错误',
                description: '请填写必填字段',
                variant: 'destructive',
            });
            return;
        }

        setLoading(true);
        try {
            const response = await AdvertisementService.createAd(newAd);

            if (response.success) {
                toast({
                    title: '成功',
                    description: '广告创建成功',
                });
                setShowCreateDialog(false);
                loadAds();
                setNewAd({
                    title: '',
                    slot_id: '',
                    ad_type: 'image',
                    content: '',
                    image_url: '',
                    link_url: '',
                    html_code: '',
                    priority: 5,
                    budget: undefined,
                });
            } else {
                toast({
                    title: '错误',
                    description: response.error || '创建失败',
                    variant: 'destructive',
                });
            }
        } catch (error) {
            console.error('Create ad failed:', error);
            toast({
                title: '错误',
                description: '创建广告失败',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    const handlePauseAd = async (adId: string) => {
        try {
            const response = await AdvertisementService.pauseAd(adId);
            if (response.success) {
                toast({title: '成功', description: '广告已暂停'});
                loadAds();
            }
        } catch (error) {
            toast({title: '错误', description: '操作失败', variant: 'destructive'});
        }
    };

    const handleActivateAd = async (adId: string) => {
        try {
            const response = await AdvertisementService.activateAd(adId);
            if (response.success) {
                toast({title: '成功', description: '广告已激活'});
                loadAds();
            }
        } catch (error) {
            toast({title: '错误', description: '操作失败', variant: 'destructive'});
        }
    };

    const handleDeleteAd = async (adId: string) => {
        if (!confirm('确定要删除这个广告吗？')) return;

        try {
            const response = await AdvertisementService.deleteAd(adId);
            if (response.success) {
                toast({title: '成功', description: '广告已删除'});
                loadAds();
            }
        } catch (error) {
            toast({title: '错误', description: '删除失败', variant: 'destructive'});
        }
    };

    const getStatusBadge = (status: string) => {
        const statusMap: Record<string, {
            label: string;
            variant: 'default' | 'secondary' | 'destructive' | 'outline'
        }> = {
            active: {label: '运行中', variant: 'default'},
            paused: {label: '已暂停', variant: 'secondary'},
            expired: {label: '已过期', variant: 'outline'},
        };
        const config = statusMap[status] || {label: status, variant: 'outline'};
        return <Badge variant={config.variant}>{config.label}</Badge>;
    };

    return (
        <div className="container mx-auto py-8 px-4">
            <h1 className="text-3xl font-bold mb-8">广告管理系统</h1>

            <Tabs defaultValue="dashboard" className="space-y-6">
                <TabsList className="grid w-full max-w-md grid-cols-3">
                    <TabsTrigger value="dashboard">数据概览</TabsTrigger>
                    <TabsTrigger value="ads">广告管理</TabsTrigger>
                    <TabsTrigger value="slots">广告位管理</TabsTrigger>
                </TabsList>

                {/* 数据概览 */}
                <TabsContent value="dashboard">
                    {revenue && (
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-sm">总展示次数</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <p className="text-3xl font-bold">{revenue.total_impressions.toLocaleString()}</p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-sm">总点击次数</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <p className="text-3xl font-bold">{revenue.total_clicks.toLocaleString()}</p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-sm">点击率 (CTR)</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <p className="text-3xl font-bold">{revenue.ctr}%</p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-sm">总收益</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <p className="text-3xl font-bold text-green-600">¥{revenue.total_revenue.toFixed(2)}</p>
                                </CardContent>
                            </Card>
                        </div>
                    )}
                </TabsContent>

                {/* 广告管理 */}
                <TabsContent value="ads" className="space-y-4">
                    <div className="flex justify-between items-center">
                        <h2 className="text-xl font-semibold">广告列表</h2>
                        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
                            <DialogTrigger asChild>
                                <Button>创建广告</Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-2xl">
                                <DialogHeader>
                                    <DialogTitle>创建新广告</DialogTitle>
                                    <DialogDescription>填写广告信息并选择投放位置</DialogDescription>
                                </DialogHeader>
                                <div className="space-y-4 py-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="title">广告标题</Label>
                                        <Input
                                            id="title"
                                            value={newAd.title}
                                            onChange={(e) => setNewAd({...newAd, title: e.target.value})}
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="slot">广告位</Label>
                                        <Select value={newAd.slot_id}
                                                onValueChange={(v) => setNewAd({...newAd, slot_id: v})}>
                                            <SelectTrigger>
                                                <SelectValue placeholder="选择广告位"/>
                                            </SelectTrigger>
                                            <SelectContent>
                                                {slots.map((slot) => (
                                                    <SelectItem key={slot.slot_id} value={slot.slot_id}>
                                                        {slot.name} ({slot.width}x{slot.height})
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="type">广告类型</Label>
                                        <Select value={newAd.ad_type}
                                                onValueChange={(v) => setNewAd({...newAd, ad_type: v})}>
                                            <SelectTrigger>
                                                <SelectValue/>
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="image">图片广告</SelectItem>
                                                <SelectItem value="html">HTML代码</SelectItem>
                                                <SelectItem value="adsense">Google AdSense</SelectItem>
                                                <SelectItem value="baidu">百度联盟</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    {newAd.ad_type === 'image' && (
                                        <>
                                            <div className="space-y-2">
                                                <Label htmlFor="image_url">图片URL</Label>
                                                <Input
                                                    id="image_url"
                                                    value={newAd.image_url}
                                                    onChange={(e) => setNewAd({...newAd, image_url: e.target.value})}
                                                />
                                            </div>
                                            <div className="space-y-2">
                                                <Label htmlFor="link_url">跳转链接</Label>
                                                <Input
                                                    id="link_url"
                                                    value={newAd.link_url}
                                                    onChange={(e) => setNewAd({...newAd, link_url: e.target.value})}
                                                />
                                            </div>
                                        </>
                                    )}

                                    {newAd.ad_type === 'html' && (
                                        <div className="space-y-2">
                                            <Label htmlFor="html_code">HTML代码</Label>
                                            <textarea
                                                id="html_code"
                                                className="w-full min-h-[150px] p-2 border rounded"
                                                value={newAd.html_code}
                                                onChange={(e) => setNewAd({...newAd, html_code: e.target.value})}
                                            />
                                        </div>
                                    )}

                                    <div className="space-y-2">
                                        <Label htmlFor="priority">优先级 (1-10)</Label>
                                        <Input
                                            id="priority"
                                            type="number"
                                            min="1"
                                            max="10"
                                            value={newAd.priority}
                                            onChange={(e) => setNewAd({...newAd, priority: parseInt(e.target.value)})}
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="budget">预算上限 (可选)</Label>
                                        <Input
                                            id="budget"
                                            type="number"
                                            value={newAd.budget || ''}
                                            onChange={(e) => setNewAd({
                                                ...newAd,
                                                budget: parseFloat(e.target.value) || undefined
                                            })}
                                        />
                                    </div>

                                    <Button onClick={handleCreateAd} disabled={loading} className="w-full">
                                        {loading ? '创建中...' : '创建广告'}
                                    </Button>
                                </div>
                            </DialogContent>
                        </Dialog>
                    </div>

                    <div className="space-y-4">
                        {ads.length === 0 ? (
                            <Card>
                                <CardContent className="py-8 text-center text-muted-foreground">
                                    暂无广告，点击上方按钮创建
                                </CardContent>
                            </Card>
                        ) : (
                            ads.map((ad) => (
                                <Card key={ad.ad_id}>
                                    <CardHeader>
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <CardTitle className="text-lg">{ad.title}</CardTitle>
                                                <CardDescription>
                                                    {slots.find(s => s.slot_id === ad.slot_id)?.name || ad.slot_id}
                                                </CardDescription>
                                            </div>
                                            {getStatusBadge(ad.status)}
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="flex justify-between items-center">
                                            <div className="text-sm text-muted-foreground">
                                                <p>类型: {ad.ad_type}</p>
                                                <p>优先级: {ad.priority}</p>
                                                {ad.budget && <p>预算: ¥{ad.budget} (已用: ¥{ad.spent})</p>}
                                            </div>
                                            <div className="space-x-2">
                                                {ad.status === 'active' ? (
                                                    <Button size="sm" variant="outline"
                                                            onClick={() => handlePauseAd(ad.ad_id)}>
                                                        暂停
                                                    </Button>
                                                ) : (
                                                    <Button size="sm" onClick={() => handleActivateAd(ad.ad_id)}>
                                                        激活
                                                    </Button>
                                                )}
                                                <Button size="sm" variant="destructive"
                                                        onClick={() => handleDeleteAd(ad.ad_id)}>
                                                    删除
                                                </Button>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))
                        )}
                    </div>
                </TabsContent>

                {/* 广告位管理 */}
                <TabsContent value="slots">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {slots.map((slot) => (
                            <Card key={slot.slot_id}>
                                <CardHeader>
                                    <CardTitle>{slot.name}</CardTitle>
                                    <CardDescription>{slot.description}</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-2">
                                        <p className="text-sm">位置: {slot.position}</p>
                                        <p className="text-sm">尺寸: {slot.width} x {slot.height}</p>
                                        {slot.stats && (
                                            <>
                                                <p className="text-sm">活跃广告: {slot.stats.active_ads}</p>
                                                <p className="text-sm">总展示: {slot.stats.total_impressions}</p>
                                                <p className="text-sm">点击率: {slot.stats.ctr}%</p>
                                            </>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </TabsContent>
            </Tabs>
        </div>
    );
}
