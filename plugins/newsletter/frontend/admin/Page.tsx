'use client';

import React, {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {Mail, Users, UserCheck, UserX, Send} from 'lucide-react';
import {NewsletterService} from '../api';

function NewsletterManager() {
  const [page, setPage] = useState(1);

  const {data: subscribers = {data: [], total: 0, page: 1}} = useQuery({
    queryKey: ['newsletter-subscribers', page],
    queryFn: () => NewsletterService.list(page, 50),
    placeholderData: (prev: any) => prev || {data: [], total: 0, page: 1},
  });

  const {data: stats = {total: 0, active: 0, unsubscribed: 0}} = useQuery({
    queryKey: ['newsletter-stats'],
    queryFn: () => NewsletterService.stats(),
    placeholderData: (prev: any) => prev || {total: 0, active: 0, unsubscribed: 0},
  });

  return (
    <AdminShell title="Newsletter Management" actions={
      <div className="flex items-center gap-4 text-sm">
        <span className="flex items-center gap-1 text-gray-500"><Users className="w-4 h-4"/>{stats.total} total</span>
        <span className="flex items-center gap-1 text-green-600"><UserCheck className="w-4 h-4"/>{stats.active} active</span>
        <span className="flex items-center gap-1 text-gray-400"><UserX className="w-4 h-4"/>{stats.unsubscribed} unsubscribed</span>
      </div>
    }>
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-800 text-xs text-gray-500 uppercase">
                <th className="text-left px-4 py-3 font-medium">Email</th>
                <th className="text-left px-4 py-3 font-medium">Name</th>
                <th className="text-left px-4 py-3 font-medium">Source</th>
                <th className="text-left px-4 py-3 font-medium">Subscribed</th>
                <th className="text-center px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {(subscribers as any).data?.map((sub: any) => (
                <tr key={sub.id} className="border-b border-gray-100 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">{sub.email}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{sub.name || '-'}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{sub.source}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{sub.subscribed_at ? new Date(sub.subscribed_at).toLocaleDateString() : '-'}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${sub.is_active ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400' : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'}`}>
                      {sub.is_active ? 'Active' : 'Unsubscribed'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {(subscribers as any).total > 50 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-800">
            <span className="text-sm text-gray-500">{(subscribers as any).total} total</span>
            <div className="flex gap-2">
              <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                      className="px-3 py-1 text-sm border border-gray-200 dark:border-gray-700 rounded-lg disabled:opacity-50">Previous</button>
              <button disabled={(subscribers as any).data?.length < 50} onClick={() => setPage(p => p + 1)}
                      className="px-3 py-1 text-sm border border-gray-200 dark:border-gray-700 rounded-lg disabled:opacity-50">Next</button>
            </div>
          </div>
        )}
      </div>

      {stats.total === 0 && (
        <div className="text-center py-16 text-gray-400">
          <Mail className="w-12 h-12 mx-auto mb-4 opacity-50"/>
          <p className="text-lg font-medium text-gray-500 dark:text-gray-400">No subscribers yet</p>
          <p className="text-sm mt-1">The newsletter signup form on the homepage will collect emails here</p>
        </div>
      )}
    </AdminShell>
  );
}

export default function AdminNewsletter() {
  return <AuthGuard><QueryProvider><NewsletterManager/></QueryProvider></AuthGuard>;
}
