'use client';

import React from 'react';
import Sidebar from '@/components/layout/Sidebar';
import Navbar from '@/components/layout/Navbar';
import AIModeHeader from '@/ai-mode/components/AIModeHeader';
import AIModeSettings from '@/ai-mode/components/AIModeSettings';

export default function AIModeSettingsPage() {
  return (
    <div className="flex h-screen bg-zinc-50 overflow-hidden font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Navbar />
        <AIModeHeader activeTab="settings" />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            <AIModeSettings />
          </div>
        </main>
      </div>
    </div>
  );
}
