'use client';

import React from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api';
import {Diamond, Image as ImageIcon, CheckCircle, ExternalLink} from 'lucide-react';

function ExtNFTInner() {
  const {data:nfts}=useQuery({queryKey:['ext-nft'],queryFn:async()=>{const r=await apiClient.get<any[]>('/ext/nft');return r.success&&r.data?(Array.isArray(r.data)?r.data:r.data.nfts||[]):[]}});

  return (
    <AdminShell title="NFT 管理">
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
        <div className="flex items-center gap-4"><Diamond className="w-10 h-10 text-purple-600"/><div><p className="font-bold text-gray-900 dark:text-white">NFT 功能</p><p className="text-sm text-gray-500">将文章铸造成 NFT，支持转移和验证</p></div></div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {nfts?.length>0?nfts.map((n:any,i:number)=>(
          <div key={i} className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
            <div className="aspect-square bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-xl flex items-center justify-center mb-3">
              {n.image_url?<img src={n.image_url} alt="" className="w-full h-full object-cover rounded-xl"/>:<ImageIcon className="w-12 h-12 text-gray-300"/>}
            </div>
            <h3 className="font-semibold text-sm text-gray-900 dark:text-white truncate">{n.name||n.token_id||'NFT'}</h3>
            <p className="text-xs text-gray-500 mt-1">{n.collection||n.contract_address||''}</p>
            <div className="flex items-center justify-between mt-3">
              <span className="flex items-center gap-1 text-xs text-green-600"><CheckCircle className="w-3 h-3"/>已验证</span>
              {n.explorer_url&&<a href={n.explorer_url} target="_blank" className="text-xs text-blue-600 hover:underline flex items-center gap-0.5"><ExternalLink className="w-3 h-3"/>查看</a>}
            </div>
          </div>
        )):<div className="col-span-full p-12 text-center text-gray-400"><Diamond className="w-10 h-10 mx-auto mb-3 opacity-40"/><p>暂无 NFT</p></div>}
      </div>
    </AdminShell>
  );
}
export default function ExtNFT(){return <AuthGuard><QueryProvider><ExtNFTInner/></QueryProvider></AuthGuard>;}
