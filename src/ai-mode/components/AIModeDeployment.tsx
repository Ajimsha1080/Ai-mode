'use client';

import React, { useEffect, useState } from 'react';
import {
  Globe,
  Copy,
  Check,
  Plus,
  RefreshCw,
  Palette,
  Shield,
  Eye,
  Sparkles,
  ExternalLink
} from 'lucide-react';
import { AIModeApiClient } from '../services/ai-mode-api';
import type { AIModeDeployment as AIModeDeploymentData } from '../types';

export default function AIModeDeployment() {
  const [deployments, setDeployments] = useState<AIModeDeploymentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [activeDeployment, setActiveDeployment] = useState<AIModeDeploymentData | null>(null);
  const [saving, setSaving] = useState(false);

  // Edit form state
  const [launcherText, setLauncherText] = useState('Ask AI Mode');
  const [welcomeMessage, setWelcomeMessage] = useState('Hi! 👋 Welcome to our store. How can I help you today?');
  const [primaryColor, setPrimaryColor] = useState('#6366f1');
  const [position, setPosition] = useState('bottom_right');
  const [allowedDomains, setAllowedDomains] = useState('*');

  const fetchDeployments = async () => {
    try {
      setLoading(true);
      const data = await AIModeApiClient.getDeployments();
      setDeployments(data);
      if (data.length > 0) {
        const first = data[0];
        setActiveDeployment(first);
        setLauncherText(first.launcher_text || 'Ask AI Mode');
        setWelcomeMessage(first.welcome_message || '');
        setPrimaryColor(first.theme_config?.primaryColor || '#6366f1');
        setPosition(first.theme_config?.position || 'bottom_right');
        setAllowedDomains(first.allowed_domains?.join(', ') || '*');
      }
    } catch (err: any) {
      alert(`Failed to load deployments: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeployments();
  }, []);

  const handleCreateNew = async () => {
    try {
      setLoading(true);
      await AIModeApiClient.createDeployment({
        name: 'New AI Mode Widget',
        welcome_message: 'Hi! 👋 How can I help you discover products today?',
        launcher_text: 'Ask AI Mode'
      });
      await fetchDeployments();
    } catch (err: any) {
      alert(`Failed to create deployment: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveCustomization = async () => {
    if (!activeDeployment) return;
    setSaving(true);
    try {
      const domainsList = allowedDomains.split(',').map((d) => d.trim()).filter(Boolean);
      await AIModeApiClient.updateDeployment(activeDeployment.id, {
        launcher_text: launcherText,
        welcome_message: welcomeMessage,
        allowed_domains: domainsList.length > 0 ? domainsList : ['*'],
        theme_config: {
          ...activeDeployment.theme_config,
          primaryColor,
          position
        }
      });
      await fetchDeployments();
      alert('Deployment settings saved successfully!');
    } catch (err: any) {
      alert(`Save error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const copyEmbedCode = (code: string, id: string) => {
    navigator.clipboard.writeText(code);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2500);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-zinc-200 shadow-xs">
        <div>
          <h2 className="text-lg font-bold text-zinc-900">AI Mode Widget Deployment</h2>
          <p className="text-xs text-zinc-500 mt-1">
            Deploy an isolated AI Mode shopping widget on your storefront. Fully decoupled from existing widgets.
          </p>
        </div>
        <button
          onClick={handleCreateNew}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-xs transition active:scale-95"
        >
          <Plus className="w-4 h-4" />
          Create New Deployment
        </button>
      </div>

      {loading ? (
        <div className="p-12 text-center text-zinc-400 bg-white rounded-2xl border border-zinc-200">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-600" />
          <p className="text-xs">Loading deployment configuration...</p>
        </div>
      ) : deployments.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-2xl border border-dashed border-zinc-300">
          <Globe className="w-10 h-10 text-zinc-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-zinc-800">No AI Mode Deployments Yet</h3>
          <button
            onClick={handleCreateNew}
            className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-2 bg-zinc-900 text-white text-xs font-semibold rounded-xl hover:bg-zinc-800 transition"
          >
            <Plus className="w-3.5 h-3.5" />
            Create First Widget
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Customization Editor (8 Cols) */}
          <div className="lg:col-span-7 space-y-6">
            <div className="bg-white p-6 rounded-3xl border border-zinc-200 shadow-xs space-y-5">
              <div className="flex items-center justify-between border-b border-zinc-100 pb-4">
                <div className="flex items-center gap-2">
                  <Palette className="w-5 h-5 text-indigo-600" />
                  <h3 className="font-bold text-zinc-900 text-sm">Widget Customization</h3>
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  ● Status: {activeDeployment?.status}
                </span>
              </div>

              <div className="space-y-4 text-xs">
                <div>
                  <label className="block font-semibold text-zinc-700 mb-1">Launcher Button Text</label>
                  <input
                    type="text"
                    value={launcherText}
                    onChange={(e) => setLauncherText(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl border border-zinc-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-zinc-700 mb-1">Welcome / Greeting Message</label>
                  <textarea
                    rows={2}
                    value={welcomeMessage}
                    onChange={(e) => setWelcomeMessage(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl border border-zinc-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block font-semibold text-zinc-700 mb-1">Primary Color</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={primaryColor}
                        onChange={(e) => setPrimaryColor(e.target.value)}
                        className="w-10 h-10 rounded-xl border border-zinc-200 cursor-pointer"
                      />
                      <span className="font-mono text-xs text-zinc-700 font-semibold">{primaryColor}</span>
                    </div>
                  </div>

                  <div>
                    <label className="block font-semibold text-zinc-700 mb-1">Widget Position</label>
                    <select
                      value={position}
                      onChange={(e) => setPosition(e.target.value)}
                      className="w-full px-3.5 py-2 rounded-xl border border-zinc-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 text-xs"
                    >
                      <option value="bottom_right">Bottom Right</option>
                      <option value="bottom_left">Bottom Left</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block font-semibold text-zinc-700 mb-1 flex items-center gap-1">
                    <Shield className="w-3.5 h-3.5 text-indigo-600" />
                    Allowed Domains (SSRF Protection)
                  </label>
                  <input
                    type="text"
                    value={allowedDomains}
                    onChange={(e) => setAllowedDomains(e.target.value)}
                    placeholder="e.g. yourstore.com, myshopify.com or * for all"
                    className="w-full px-3.5 py-2 rounded-xl border border-zinc-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 font-mono text-[11px]"
                  />
                </div>
              </div>

              <div className="pt-3 border-t border-zinc-100 flex justify-end">
                <button
                  onClick={handleSaveCustomization}
                  disabled={saving}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-xs transition"
                >
                  {saving ? 'Saving...' : 'Save Configuration'}
                </button>
              </div>
            </div>

            {/* Embed Snippet Card */}
            {activeDeployment && (
              <div className="bg-zinc-950 text-white p-6 rounded-3xl shadow-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Globe className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-bold tracking-wide uppercase text-zinc-400">
                      HTML Embed Code Snippet
                    </span>
                  </div>
                  <button
                    onClick={() => copyEmbedCode(activeDeployment.embed_code, activeDeployment.id)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold rounded-xl backdrop-blur-xs transition active:scale-95"
                  >
                    {copiedId === activeDeployment.id ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        Copy Embed Code
                      </>
                    )}
                  </button>
                </div>

                <pre className="p-4 bg-zinc-900 rounded-2xl text-[11px] font-mono text-indigo-300 overflow-x-auto border border-white/5">
                  <code>{activeDeployment.embed_code}</code>
                </pre>

                <p className="text-[11px] text-zinc-400">
                  Paste this snippet right before the closing <code className="text-zinc-200">&lt;/body&gt;</code> tag of your store template.
                </p>
              </div>
            )}
          </div>

          {/* Interactive Widget Simulator Frame (5 Cols) */}
          <div className="lg:col-span-5">
            <div className="sticky top-24 bg-zinc-900 rounded-3xl p-5 border border-zinc-800 shadow-2xl space-y-3">
              <div className="flex items-center justify-between text-white text-xs font-bold">
                <span className="flex items-center gap-1.5">
                  <Eye className="w-4 h-4 text-indigo-400" />
                  Live Widget Preview
                </span>
                <span className="text-[10px] text-zinc-400 font-mono">{position}</span>
              </div>

              {/* Simulated Browser Viewport */}
              <div className="relative w-full h-[520px] bg-zinc-950 rounded-2xl border border-zinc-800 overflow-hidden flex flex-col justify-end p-4">
                {/* Mock Store Background */}
                <div className="absolute inset-0 p-4 opacity-20 pointer-events-none text-zinc-400 text-xs">
                  <div className="w-24 h-4 bg-zinc-700 rounded-md mb-4" />
                  <div className="grid grid-cols-2 gap-2">
                    <div className="h-24 bg-zinc-800 rounded-xl" />
                    <div className="h-24 bg-zinc-800 rounded-xl" />
                  </div>
                </div>

                {/* Simulated Floating Chat Window */}
                <div className="relative z-10 bg-white rounded-2xl shadow-2xl border border-zinc-200 p-4 space-y-3 mb-3 animate-in fade-in slide-in-from-bottom-2">
                  <div className="flex items-center justify-between border-b border-zinc-100 pb-2.5">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs"
                        style={{ backgroundColor: primaryColor }}
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                      </div>
                      <div className="text-xs font-bold text-zinc-900">AI Mode Concierge</div>
                    </div>
                  </div>

                  <div className="text-xs text-zinc-700 bg-zinc-50 p-2.5 rounded-xl">
                    {welcomeMessage}
                  </div>

                  <div className="flex flex-wrap gap-1">
                    <span className="text-[10px] px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full font-medium">
                      Show Jackets
                    </span>
                    <span className="text-[10px] px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full font-medium">
                      Items under ₹1,000
                    </span>
                  </div>
                </div>

                {/* Floating Launcher Button */}
                <div className={`relative z-10 flex ${position === 'bottom_left' ? 'justify-start' : 'justify-end'}`}>
                  <button
                    className="flex items-center gap-2 px-4 py-2.5 rounded-full text-white text-xs font-bold shadow-lg transition-transform hover:scale-105"
                    style={{ backgroundColor: primaryColor }}
                  >
                    <Sparkles className="w-4 h-4" />
                    {launcherText}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
