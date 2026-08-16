'use client';

/**
 * 首页订阅 - 编辑式单行订阅条
 * - 无渐变大色块：细线上边 + 衬线小标题 + 深色输入 + 单按钮
 */
import React, {useState} from 'react';
import {motion} from 'framer-motion';
import {ArrowRight, Check, Loader2} from 'lucide-react';
import {fadeUp, Section} from './_shared';
import {apiClient} from '@/lib/api/base-client';

interface Props {
  title: string;
  subtitle: string;
  buttonText: string;
}

export default function HomeNewsletter({title, subtitle, buttonText}: Props) {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !email.includes('@')) return;
    setStatus('loading');
    try {
      const res = await apiClient.post('/plugins/newsletter/action', {
        action: 'subscribe',
        params: {email, source: 'homepage'},
      });
      setStatus(res.success ? 'success' : 'error');
    } catch {
      setStatus('error');
    }
  };

  return (
    <Section className="relative bg-[#05070f]">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 py-16 sm:py-20">
        <motion.div variants={fadeUp} className="border-t border-white/10 pt-12">
          <div className="grid lg:grid-cols-2 gap-8 items-center">
            <div>
              <h2 className="font-serif text-2xl sm:text-3xl font-semibold text-slate-100 tracking-tight">
                {title || '订阅更新'}
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-400 max-w-md">
                {subtitle}
              </p>
            </div>

            <div className="lg:justify-self-end w-full max-w-md">
              {status === 'success' ? (
                <p className="inline-flex items-center gap-2 text-sm font-medium text-emerald-400">
                  <Check className="w-4 h-4"/>
                  订阅成功，感谢支持！
                </p>
              ) : (
                <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    placeholder="输入你的邮箱地址"
                    aria-label="邮箱地址"
                    className="flex-1 min-w-0 px-4 py-3 rounded-lg bg-slate-900/80 border border-white/10 text-sm text-slate-100
                      placeholder:text-slate-600 focus:outline-none focus:border-blue-500/60 focus:ring-2 focus:ring-blue-500/20
                      transition-colors duration-200"
                    disabled={status === 'loading'}
                  />
                  <button
                    type="submit"
                    disabled={status === 'loading'}
                    className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-blue-600 text-white text-sm font-semibold
                      hover:bg-blue-500 transition-colors duration-300 active:scale-[0.98] disabled:opacity-50 whitespace-nowrap"
                  >
                    {status === 'loading'
                      ? <Loader2 className="w-4 h-4 animate-spin"/>
                      : <><ArrowRight className="w-4 h-4"/>{buttonText || '订阅'}</>}
                  </button>
                </form>
              )}
              {status === 'error' && (
                <p className="mt-3 text-sm text-red-400">订阅失败，请稍后重试。</p>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </Section>
  );
}
