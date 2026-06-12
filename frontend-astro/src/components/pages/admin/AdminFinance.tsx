'use client';

import React, {lazy, Suspense, useState} from 'react';
import {CreditCard, DollarSign, Settings, Banknote, PieChart, ArrowLeftRight} from 'lucide-react';
import {AdminShell} from '@/components/admin/AdminShell';
import {QueryProvider} from '@/components/QueryProvider';

const LazyGatewaysTab = lazy(() => import('./payment/GatewaysTab'));
const LazyTransactionsTab = lazy(() => import('./payment/TransactionsTab'));
const LazyTaxConfigsTab = lazy(() => import('./payment/TaxConfigsTab'));
const LazyRecordsTab = lazy(() => import('./revenue/RecordsTab'));
const LazyPayoutsTab = lazy(() => import('./revenue/PayoutsTab'));
const LazyConfigTab = lazy(() => import('./revenue/ConfigTab'));
const LazyStatsTab = lazy(() => import('./revenue/StatsTab'));

type TabKey = 'gateways' | 'transactions' | 'tax' | 'records' | 'payouts' | 'config' | 'stats';

interface TabDef {
  key: TabKey;
  label: string;
  icon: React.FC<{ className?: string }>;
  group: 'payment' | 'revenue';
}

// Use unicode escapes to avoid encoding issues
const TABS: TabDef[] = [
  {key: 'gateways', label: '\u652f\u4ed8\u7f51\u5173', icon: CreditCard, group: 'payment'},
  {key: 'transactions', label: '\u4ea4\u6613\u8bb0\u5f55', icon: ArrowLeftRight, group: 'payment'},
  {key: 'tax', label: '\u7a0e\u52a1\u914d\u7f6e', icon: Settings, group: 'payment'},
  {key: 'records', label: '\u6536\u76ca\u8bb0\u5f55', icon: DollarSign, group: 'revenue'},
  {key: 'payouts', label: '\u63d0\u73b0\u7ba1\u7406', icon: Banknote, group: 'revenue'},
  {key: 'config', label: '\u5206\u6210\u914d\u7f6e', icon: Settings, group: 'revenue'},
  {key: 'stats', label: '\u5e73\u53f0\u7edf\u8ba1', icon: PieChart, group: 'revenue'},
];

const PAYMENT_TITLE = '\u652f\u4ed8\u7ba1\u7406';
const REVENUE_TITLE = '\u6536\u76ca\u7ba1\u7406';
const PAYMENT_BTN = '\u652f\u4ed8\u7ba1\u7406';
const REVENUE_BTN = '\u6536\u76ca\u7ba1\u7406';

const TabSkeleton = () => (
  <div className="space-y-4 animate-pulse">
    <div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded-lg"/>
    <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded-xl"/>
    <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded-xl"/>
  </div>
);

function FinanceInner() {
  const [tab, setTab] = useState<TabKey>('gateways');
  const [group, setGroup] = useState<'payment' | 'revenue'>('payment');

  const visibleTabs = TABS.filter(t => t.group === group);

  return (
    <AdminShell title={group === 'payment' ? PAYMENT_TITLE : REVENUE_TITLE}>
      <div className="space-y-6">
        <div className="flex gap-2">
          <button onClick={() => { setGroup('payment'); setTab('gateways'); }}
            className={`px-5 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${
              group === 'payment' ? 'bg-blue-600 text-white shadow-sm' : 'bg-white dark:bg-gray-900 border hover:bg-gray-50 dark:hover:bg-gray-800'
            }`}>
            <CreditCard className="w-4 h-4"/>{PAYMENT_BTN}
          </button>
          <button onClick={() => { setGroup('revenue'); setTab('records'); }}
            className={`px-5 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${
              group === 'revenue' ? 'bg-blue-600 text-white shadow-sm' : 'bg-white dark:bg-gray-900 border hover:bg-gray-50 dark:hover:bg-gray-800'
            }`}>
            <PieChart className="w-4 h-4"/>{REVENUE_BTN}
          </button>
        </div>

        <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-xl p-1">
          {visibleTabs.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm rounded-lg transition-colors ${
                tab === t.key ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm font-medium' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}>
              <t.icon className="w-4 h-4"/>{t.label}
            </button>
          ))}
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
          <Suspense fallback={<TabSkeleton/>}>
            {tab === 'gateways' && <LazyGatewaysTab/>}
            {tab === 'transactions' && <LazyTransactionsTab/>}
            {tab === 'tax' && <LazyTaxConfigsTab/>}
            {tab === 'records' && <LazyRecordsTab/>}
            {tab === 'payouts' && <LazyPayoutsTab/>}
            {tab === 'config' && <LazyConfigTab/>}
            {tab === 'stats' && <LazyStatsTab/>}
          </Suspense>
        </div>
      </div>
    </AdminShell>
  );
}

export default function AdminFinance() {
  return <QueryProvider><FinanceInner/></QueryProvider>;
}
