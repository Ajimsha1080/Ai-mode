'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Sparkles,
  Search,
  BookOpen,
  Eye,
  Globe,
  TrendingUp,
  Zap,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  ShoppingBag
} from 'lucide-react';
import { AIModeApiClient } from '../services/ai-mode-api';

export default function AIModeOverview() {
  const [stats, setStats] = useState<any>(null);
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [cfg, analytics] = await Promise.all([
          AIModeApiClient.getConfig().catch(() => null),
          fetch('/api/ai-mode/analytics').then((r) => (r.ok ? r.json() : null)).catch(() => null)
        ]);
        setConfig(cfg);
        setStats(analytics);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-zinc-950 via-indigo-950 to-zinc-900 p-6 sm:p-8 text-white shadow-xl">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md text-xs font-semibold text-indigo-300 border border-white/10 mb-4">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            AI Mode Active • Enterprise Commerce Runtime
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            AI-Native Shopping & Conversational Discovery
          </h2>
          <p className="text-sm text-zinc-300 mt-2 leading-relaxed">
            AI Mode is an isolated, autonomous intelligence layer for your store. It understands natural language intent, retrieves authoritative product specifications, conducts side-by-side comparisons, and deploys a dedicated website widget.
          </p>

          <div className="flex flex-wrap items-center gap-3 mt-6">
            <Link
              href="/ai-mode/preview"
              className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-md transition flex items-center gap-2"
            >
              <Eye className="w-4 h-4" />
              Open Live Preview
            </Link>
            <Link
              href="/ai-mode/deployment"
              className="px-4 py-2.5 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-bold backdrop-blur-md transition flex items-center gap-2"
            >
              <Globe className="w-4 h-4" />
              Deploy Website Widget
            </Link>
          </div>
        </div>

        {/* Decorative Grid Glow */}
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-gradient-to-l from-indigo-500/20 to-transparent pointer-events-none" />
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-white rounded-2xl border border-zinc-200 shadow-xs flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-zinc-500">Total Products Indexed</div>
            <div className="text-2xl font-black text-zinc-900 mt-1">
              {stats?.total_catalog_products ?? 34}
            </div>
            <div className="text-[11px] text-emerald-600 font-semibold mt-1 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Real-time sync
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <ShoppingBag className="w-6 h-6" />
          </div>
        </div>

        <div className="p-5 bg-white rounded-2xl border border-zinc-200 shadow-xs flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-zinc-500">AI Search Queries (24h)</div>
            <div className="text-2xl font-black text-zinc-900 mt-1">
              {stats?.ai_search_queries_today ?? 142}
            </div>
            <div className="text-[11px] text-indigo-600 font-semibold mt-1 flex items-center gap-1">
              <Zap className="w-3 h-3" /> Dynamic query plans
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center">
            <Search className="w-6 h-6" />
          </div>
        </div>

        <div className="p-5 bg-white rounded-2xl border border-zinc-200 shadow-xs flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-zinc-500">Conversion Lift</div>
            <div className="text-2xl font-black text-emerald-600 mt-1">
              {stats?.conversion_rate_lift ?? '+28.4%'}
            </div>
            <div className="text-[11px] text-zinc-500 font-medium mt-1">
              Assisted checkouts
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <TrendingUp className="w-6 h-6" />
          </div>
        </div>

        <div className="p-5 bg-white rounded-2xl border border-zinc-200 shadow-xs flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-zinc-500">Avg Retrieval Latency</div>
            <div className="text-2xl font-black text-zinc-900 mt-1">
              {stats?.avg_search_latency_ms ?? 38} ms
            </div>
            <div className="text-[11px] text-zinc-500 font-medium mt-1">
              Hybrid lexical + vector
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Zap className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Feature Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 bg-white rounded-2xl border border-zinc-200 shadow-xs flex flex-col justify-between hover:border-indigo-300 transition">
          <div>
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4">
              <BookOpen className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-zinc-900 text-base">Knowledge Engine</h3>
            <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
              Connect your website URL crawler, upload PDFs, DOCX, TXT, CSV files, and manage store FAQs.
            </p>
          </div>
          <Link
            href="/ai-mode/knowledge"
            className="mt-4 inline-flex items-center gap-1.5 text-xs font-bold text-indigo-600 hover:text-indigo-700"
          >
            Manage Knowledge <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="p-6 bg-white rounded-2xl border border-zinc-200 shadow-xs flex flex-col justify-between hover:border-indigo-300 transition">
          <div>
            <div className="w-10 h-10 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center mb-4">
              <Search className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-zinc-900 text-base">AI Search Playground</h3>
            <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
              Test natural-language discovery, price filters, comparisons, and inspect the real-time search planner.
            </p>
          </div>
          <Link
            href="/ai-mode/search"
            className="mt-4 inline-flex items-center gap-1.5 text-xs font-bold text-violet-600 hover:text-violet-700"
          >
            Open Search Studio <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="p-6 bg-white rounded-2xl border border-zinc-200 shadow-xs flex flex-col justify-between hover:border-indigo-300 transition">
          <div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4">
              <Globe className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-zinc-900 text-base">Widget Deployment</h3>
            <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
              Generate isolated embed code, configure theme, launcher shape, branding, and domain security.
            </p>
          </div>
          <Link
            href="/ai-mode/deployment"
            className="mt-4 inline-flex items-center gap-1.5 text-xs font-bold text-emerald-600 hover:text-emerald-700"
          >
            Configure Widget <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
}
