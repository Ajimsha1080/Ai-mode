'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Sparkles, BookOpen, Search, Eye, Globe, Settings, BarChart2 } from 'lucide-react';

interface AIModeHeaderProps {
  activeTab?: string;
}

export default function AIModeHeader({ activeTab }: AIModeHeaderProps) {
  const pathname = usePathname();

  const tabs = [
    { id: 'overview', name: 'Overview', href: '/ai-mode', icon: BarChart2 },
    { id: 'knowledge', name: 'Knowledge', href: '/ai-mode/knowledge', icon: BookOpen },
    { id: 'search', name: 'AI Search', href: '/ai-mode/search', icon: Search },
    { id: 'preview', name: 'Preview', href: '/ai-mode/preview', icon: Eye },
    { id: 'deployment', name: 'Deployment', href: '/ai-mode/deployment', icon: Globe },
    { id: 'settings', name: 'Settings', href: '/ai-mode/settings', icon: Settings },
  ];

  return (
    <div className="border-b border-zinc-200 bg-white sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-md shadow-indigo-100">
              <Sparkles className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-zinc-900 tracking-tight">AI Mode</h1>
                <span className="px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/60">
                  Native Feature
                </span>
              </div>
              <p className="text-xs text-zinc-500">Autonomous conversational search, discovery & widget runtime</p>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              FastAPI Engine Active
            </span>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="flex space-x-6 overflow-x-auto no-scrollbar">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab ? activeTab === tab.id : pathname === tab.href;

            return (
              <Link
                key={tab.id}
                href={tab.href}
                className={`flex items-center gap-2 py-3 px-1 border-b-2 text-xs font-semibold whitespace-nowrap transition-colors ${
                  isActive
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-zinc-500 hover:text-zinc-800 hover:border-zinc-300'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-600' : 'text-zinc-400'}`} />
                {tab.name}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
