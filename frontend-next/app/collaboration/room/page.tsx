'use client';

import React, {Suspense, useEffect, useMemo, useState} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';
import dynamic from 'next/dynamic';
import {AuthProtected} from '@/components/AuthProtected';
import LoadingState from '@/components/LoadingState';
import ErrorState from '@/components/ErrorState';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {ArrowLeft, FileText, Users} from 'lucide-react';

const YjsCollaborativeEditor = dynamic(
    () => import('@/components/YjsCollaborativeEditor'),
    {
      ssr: false,
      loading: () => <LoadingState message="加载协作编辑器中..."/>,
    }
);

interface InvitationInfo {
  invite_id: string;
  document_id: string;
  permission: string;
  expires_at: string;
  max_users: number;
  current_users: number;
}

export default function CollaborationRoomPage() {
  return (
      <AuthProtected>
        <Suspense fallback={<LoadingState message="加载协作文档中..."/>}>
          <CollaborationRoomContent/>
        </Suspense>
      </AuthProtected>
  );
}

function CollaborationRoomContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const inviteId = searchParams?.get('invite');
  const accepted = searchParams?.get('accepted') === 'true';
  const stableDocumentId = useMemo(() => inviteId || '', [inviteId]);

  const [invitation, setInvitation] = useState<InvitationInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 获取邀请信息（仅在挂载时执行一次）
  useEffect(() => {
    let isMounted = true;
    const currentInviteId = searchParams?.get('invite');

    if (!currentInviteId) {
      if (isMounted) {
        setError('无效的邀请链接');
        setLoading(false);
      }
      return;
    }

    const fetchInvitation = async () => {
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9421';
          const response = await fetch(`${baseUrl}/api/v2/collaboration/invites/${currentInviteId}`, {
          credentials: 'include',
        });

        if (!response.ok) {
          if (response.status === 404) throw new Error('邀请不存在或已撤销');
          if (response.status === 410) throw new Error('邀请已过期');
          throw new Error('获取邀请信息失败');
        }

        const data = await response.json();
        if (data.success && isMounted) {
          setInvitation(data.data);
        } else if (isMounted) {
          throw new Error('无效的邀请数据');
        }
      } catch (err) {
        if (isMounted) {
          console.error('Fetch invitation error:', err);
          setError(err instanceof Error ? err.message : '加载邀请失败');
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchInvitation();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleAcceptInvitation = async () => {
    const currentInviteId = searchParams?.get('invite');
    if (!currentInviteId) return;

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9421';
        const response = await fetch(`${baseUrl}/api/v2/collaboration/invites/${currentInviteId}/accept`, {
        method: 'POST',
        credentials: 'include',
      });

      if (!response.ok) throw new Error('接受邀请失败');

      const data = await response.json();
      if (data.success) {
        router.push(`/collaboration/room?invite=${currentInviteId}&accepted=true`);
      } else {
        alert(data.error || '接受邀请失败');
      }
    } catch (err) {
      console.error('Accept invitation error:', err);
      alert('接受邀请失败，请重试');
    }
  };

  if (loading) {
    return <LoadingState message="加载协作文档中..."/>;
  }

  if (error) {
    return (
        <div className="container mx-auto py-8 px-4">
          <ErrorState
              error={error}
              retryAction={() => window.location.href = window.location.href}
          />
          <div className="mt-4 text-center">
            <Button onClick={() => router.push('/')} variant="outline">
              <ArrowLeft className="w-4 h-4 mr-2"/>
              返回首页
            </Button>
          </div>
        </div>
    );
  }

  if (!invitation) {
    return <ErrorState error="邀请信息不存在"/>;
  }

  // 未接受邀请：显示邀请卡片
  if (!accepted) {
    return (
        <div className="container mx-auto py-8 px-4">
          <Card className="max-w-md mx-auto">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5"/>
                协作邀请 </CardTitle>
              <CardDescription>
                您被邀请参与文档协作 </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-blue-50 p-4 rounded-lg space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">文档ID：</span>
                  <span className="font-medium">{invitation.document_id}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">权限：</span>
                  <Badge variant={invitation.permission === 'edit' ? 'default' : 'secondary'}>
                    {invitation.permission === 'edit' ? '可编辑' : '仅查看'}
                  </Badge>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">人数限制：</span>
                  <span className="font-medium">{invitation.current_users}/{invitation.max_users} 人</span>
                </div>
              </div>

              <Button
                  onClick={handleAcceptInvitation}
                  className="w-full"
                  disabled={invitation.current_users >= invitation.max_users}
              >
                <Users className="w-4 h-4 mr-2"/>
                {invitation.current_users >= invitation.max_users ? '人数已满' : '接受邀请并加入'}
              </Button>

              <Button
                  onClick={() => router.push('/')}
                  variant="outline"
                  className="w-full"
              >
                拒绝
              </Button>
            </CardContent>
          </Card>
        </div>
    );
  }

// 已接受：显示协作编辑器
  return (
      <div className="min-h-screen bg-gray-50">
        <div className="bg-white border-b shadow-sm">
          <div className="container mx-auto px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => router.push('/')}
              >
                <ArrowLeft className="w-4 h-4 mr-2"/>
                返回
              </Button>
              <div>
                <h1 className="font-semibold text-lg">协作文档</h1>
                <p className="text-sm text-gray-500">{invitation.document_id}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="gap-1">
                <Users className="w-3 h-3"/>
                {invitation.permission === 'edit' ? '可编辑' : '仅查看'}
              </Badge>
            </div>
          </div>
        </div>
        <div className="container mx-auto px-4 py-6">
          <YjsCollaborativeEditor
              documentId={stableDocumentId}
              readOnly={invitation.permission !== 'edit'}
          />
        </div>
      </div>
  );
}