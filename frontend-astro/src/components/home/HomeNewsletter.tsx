'use client';

import React, {useState} from 'react';
import {motion} from 'framer-motion';
import {ArrowRight, Sparkles, Check, Loader2} from 'lucide-react';
import {Section, scaleIn, fadeUp} from './_shared';
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
      if (res.success) {
        setStatus('success');
      } else {
        setStatus('error');
      }
    } catch {
      setStatus('error');
    }
  };

  return (
    <Section className="max-w-7xl mx-auto px-6 sm:px-8 py-20 sm:py-28">
      <motion.div variants={scaleIn} className="relative rounded-3xl overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600 via-purple-600 to-blue-800" />
        <div className="absolute inset-0 opacity-30" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.08'%3E%3Ccircle cx='30' cy='30' r='2'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }} />
        <div className="absolute -top-24 -left-24 w-64 h-64 bg-blue-400/30 rounded-full blur-3xl" />
        <div className="absolute -bottom-24 -right-24 w-64 h-64 bg-purple-400/30 rounded-full blur-3xl" />

        <div className="relative z-10 p-8 sm:p-12 lg:p-16 text-center">
          <motion.div variants={fadeUp}>
            <span className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full text-sm font-medium text-white/90 border border-white/20 mb-6">
              <Sparkles className="w-4 h-4 text-amber-300" /> Newsletter
            </span>
          </motion.div>
          <motion.h2 variants={fadeUp} className="text-3xl sm:text-4xl lg:text-5xl font-black text-white mb-5 leading-tight">{title}</motion.h2>
          <motion.p variants={fadeUp} className="text-blue-100/80 text-lg mb-10 max-w-xl mx-auto leading-relaxed">{subtitle}</motion.p>

          {status === 'success' ? (
            <motion.div initial={{opacity: 0, scale: 0.9}} animate={{opacity: 1, scale: 1}} className="inline-flex items-center gap-3 px-8 py-4 bg-white/10 backdrop-blur-sm rounded-xl border border-white/20">
              <Check className="w-5 h-5 text-green-300" />
              <span className="text-white font-medium">Thanks for subscribing!</span>
            </motion.div>
          ) : (
            <motion.form variants={fadeUp} onSubmit={handleSubmit} className="flex flex-col sm:flex-row items-center justify-center gap-3 max-w-md mx-auto">
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
                     placeholder="your@email.com"
                     className="w-full px-5 py-4 rounded-xl border-0 bg-white/10 backdrop-blur-sm text-white placeholder-blue-200/60 text-sm focus:outline-none focus:ring-2 focus:ring-white/30"
                     disabled={status === 'loading'} />
              <button type="submit" disabled={status === 'loading'}
                      className="group inline-flex items-center gap-3 px-8 py-4 bg-white text-blue-700 font-bold rounded-xl hover:bg-gray-50 transition-all duration-300 shadow-xl shadow-black/10 hover:shadow-white/20 hover:-translate-y-0.5 disabled:opacity-50 whitespace-nowrap">
                {status === 'loading' ? <Loader2 className="w-5 h-5 animate-spin"/> : <><ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" /> {buttonText || 'Subscribe'}</>}
              </button>
            </motion.form>
          )}

          {status === 'error' && <p className="mt-3 text-sm text-red-200">Something went wrong. Try again later.</p>}
        </div>
      </motion.div>
    </Section>
  );
}
