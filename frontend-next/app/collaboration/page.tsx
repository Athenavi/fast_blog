'use client';

import React, {useState, useEffect} from 'react';
import {useSearchParams, useRouter} from 'next/navigation';
import {CollaborativeEditor} from '@/components/CollaborativeRichEditor';
import {InvitationManager} from '@/components/InvitationManager';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Button} from '@/components/ui/button';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {apiFetch} from '@/lib/api';

export default function CollaborationPage() {
    const searchParams = useSearchParams();
    const router = useRouter();

    const documentId = searchParams.get('doc') || '';
    const inviteId = searchParams.get('invite');

    const [token, setToken] = useState('');
    const [isEditing, setIsEditing] = useState(false);
    const [activeTab, setActiveTab] = useState('editor');
    const [inputDocId, setInputDocId] = useState(documentId);

    // 如果有邀请ID,自动接受邀请
    useEffect(() => {
        if (inviteId && documentId) {
            handleAcceptInvite(inviteId);
        }
    }, [inviteId, documentId]);

    const handleAcceptInvite = async (inviteId: string) => {
        try {
            const response = await apiFetch(`/api/v1/collaboration/invites/${inviteId}/accept`, {
                method: 'POST',
                body: JSON.stringify({}),
            });

            if (!response.ok) {
                const error = await response.json();
                alert(`邀请无效: ${error.detail}`);
                return;
            }

            const data = await response.json();
            console.log('Accepted invitation:', data);
            setIsEditing(true);
            setActiveTab('editor');
        } catch (error) {
            console.error('Accept invite error:', error);
            alert('接受邀请失败');
        }
    };

    const handleStartEdit = () => {
        if (!inputDocId) {
            alert('请输入文档ID');
            return;
        }

        // 更新URL参数
        const params = new URLSearchParams(searchParams.toString());
        params.set('doc', inputDocId);
        router.push(`/collaboration?${params.toString()}`);
        setIsEditing(true);
    };

    const handleSave = async (content: string) => {
        try {
            const response = await apiFetch(`/api/v1/collaboration/document/${documentId}/save`, {
                method: 'POST',
                body: JSON.stringify({content}),
            });

            if (!response.ok) {
                throw new Error('Failed to save');
            }

            const data = await response.json();
            console.log('Saved:', data);
            alert('文档保存成功!');
        } catch (error) {
            console.error('Save error:', error);
            alert('保存失败');
        }
    };

    if (!isEditing || !documentId) {
        return (
            <div className="container mx-auto py-8 px-4">
                <Card className="max-w-md mx-auto">
                    <CardHeader>
                        <CardTitle>实时协作富文本编辑器</CardTitle>
                        <CardDescription>
                            基于Yjs CRDT和TipTap的专业协作编辑
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="docId">文档ID</Label>
                            <Input
                                id="docId"
                                value={inputDocId}
                                onChange={(e) => setInputDocId(e.target.value)}
                                placeholder="例如: demo-1, article-123"
                            />
                        </div>

                        <Button
                            className="w-full"
                            onClick={handleStartEdit}
                            disabled={!inputDocId}
                        >
                            开始编辑
                        </Button>

                        <div className="text-sm text-gray-500 mt-4">
                            <p className="font-semibold mb-2">核心特性:</p>
                            <ul className="list-disc list-inside space-y-1">
                                <li>✅ Yjs CRDT - 冲突-free数据结构</li>
                                <li>✅ TipTap - 现代富文本编辑器</li>
                                <li>✅ 实时协同光标和选区</li>
                                <li>✅ 自动重连和离线支持</li>
                                <li>✅ 最多3人同时编辑</li>
                            </ul>
                        </div>

                        <div className="pt-4 border-t">
                            <p className="text-sm text-gray-500 mb-2">快速开始示例:</p>
                            <div className="flex flex-wrap gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                        setInputDocId('demo-1');
                                        router.push('/collaboration?doc=demo-1');
                                        setIsEditing(true);
                                    }}
                                >
                                    Demo 1
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                        setInputDocId('demo-2');
                                        router.push('/collaboration?doc=demo-2');
                                        setIsEditing(true);
                                    }}
                                >
                                    Demo 2
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                        setInputDocId('test-doc');
                                        router.push('/collaboration?doc=test-doc');
                                        setIsEditing(true);
                                    }}
                                >
                                    Test Doc
                                </Button>
                            </div>
                            <p className="text-xs text-gray-400 mt-2">
                                提示: 进入编辑器后,切换到"邀请管理"标签页创建邀请链接
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="container mx-auto py-8 px-4">
            <div className="mb-4 flex items-center justify-between">
                <h1 className="text-2xl font-bold">协作文档: {documentId}</h1>
                <Button variant="outline" size="sm" onClick={() => setIsEditing(false)}>
                    返回
                </Button>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <TabsList className="grid w-full max-w-md grid-cols-2 mb-8">
                    <TabsTrigger value="editor">📝 编辑器</TabsTrigger>
                    <TabsTrigger value="invites">🔗 邀请管理</TabsTrigger>
                </TabsList>

                <TabsContent value="editor" className="space-y-4">
                    <CollaborativeEditor
                        documentId={documentId}
                        token={token || undefined}
                        onSave={handleSave}
                    />
                </TabsContent>

                <TabsContent value="invites">
                    <InvitationManager documentId={documentId}/>
                </TabsContent>
            </Tabs>
        </div>
    );
}
