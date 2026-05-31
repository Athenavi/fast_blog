'use client';

import React, {lazy, Suspense, useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {apiClient} from '@/lib/api/api-client';

const LazyPlansTab = lazy(() => import('./vip/PlansTab'));
const LazyFeaturesTab = lazy(() => import('./vip/FeaturesTab'));
const LazyMembersTab = lazy(() => import('./vip/MembersTab'));

const TabSkeleton = () => (
  <div className="space-y-4 animate-pulse">
    <div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded-lg"/>
    <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded-xl"/>
    <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded-xl"/>
  </div>
);

function VipAdminInner() {
  const [tab, setTab] = useState<Tab>('members');
  const {data: mgmt, isLoading, refetch} = useQuery({
    queryKey: ['admin-vip'],
    queryFn: async () => {
      const r = await apiClient.get<any>('/dashboard/vip-management');
      return (r.success && r.data) ? (r.data as VipMgmtData) : {stats:{},members:[],plans:[],features:[]};
    },


export default function AdminVip() { return <AuthGuard><QueryProvider><VipAdminInner /></QueryProvider></AuthGuard>; }
