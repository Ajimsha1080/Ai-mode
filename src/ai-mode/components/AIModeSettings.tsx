'use client';

import React, { useEffect, useState } from 'react';
import { Settings, Save, Sparkles, Shield, Cpu, RefreshCw, CheckCircle2 } from 'lucide-react';
import { AIModeApiClient } from '../services/ai-mode-api';
import { AIModeConfig } from '../types';

export default function AIModeSettings() {
  const [config, setConfig] = useState<AIModeConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Form State
  const [isEnabled, setIsEnabled] = useState(true);
  const [brandName, setBrandName] = useState('AI Mode Store');
  const [systemPrompt, setSystemPrompt] = useState('You are an AI-native shopping specialist.');
  const [modelName, setModelName] = useState('sarvam-105b-conversations');
  const [temperature, setTemperature] = useState(0.2);
  const [searchThreshold, setSearchThreshold] = useState(0.35);
  const [rerankEnabled, setRerankEnabled] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const cfg = await AIModeApiClient.getConfig();
        setConfig(cfg);
        setIsEnabled(cfg.is_enabled);
        setBrandName(cfg.brand_name || 'AI Mode Store');
        setSystemPrompt(cfg.system_prompt || '');
        setModelName(cfg.model_name || 'sarvam-105b-conversations');
        setTemperature(cfg.temperature ?? 0.2);
        setSearchThreshold(cfg.search_threshold ?? 0.35);
        setRerankEnabled(cfg.rerank_enabled ?? true);
      } catch (err: any) {
        alert(`Failed to load config: ${err.message}`);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSavedSuccess(false);

    try {
      await AIModeApiClient.updateConfig({
        is_enabled: isEnabled,
        brand_name: brandName,
        system_prompt: systemPrompt,
        model_name: modelName,
        temperature,
        search_threshold: searchThreshold,
        rerank_enabled: rerankEnabled
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      alert(`Save error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-zinc-400 bg-white rounded-2xl border border-zinc-200">
        <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-600" />
        <p className="text-xs">Loading configuration settings...</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="space-y-6 max-w-4xl">
      {/* Master Feature Flag Toggle */}
      <div className="bg-white p-6 rounded-3xl border border-zinc-200 shadow-xs flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-zinc-900 text-sm">AI Mode Feature Flag</h3>
            <span
              className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
                isEnabled ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-zinc-100 text-zinc-500'
              }`}
            >
              {isEnabled ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>
          <p className="text-xs text-zinc-500 mt-1">
            Toggle AI Mode on or off for this workspace without affecting the existing store application.
          </p>
        </div>

        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={isEnabled}
            onChange={(e) => setIsEnabled(e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-zinc-200 peer-focus:outline-hidden rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
        </label>
      </div>

      {/* Model & Reasoning Settings */}
      <div className="bg-white p-6 rounded-3xl border border-zinc-200 shadow-xs space-y-5">
        <div className="flex items-center gap-2 border-b border-zinc-100 pb-3">
          <Cpu className="w-4 h-4 text-indigo-600" />
          <h3 className="font-bold text-zinc-900 text-sm">Model Architecture & NLU</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="block font-semibold text-zinc-700 mb-1">Store Brand Name</label>
            <input
              type="text"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl border border-zinc-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-zinc-700 mb-1">Primary Reasoning Model</label>
            <select
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl border border-zinc-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 text-xs"
            >
              <option value="sarvam-105b-conversations">Sarvam 105B Conversations (Fast & Multilingual)</option>
              <option value="gpt-4o-mini">GPT-4o Mini (OpenAI)</option>
              <option value="claude-3-5-sonnet">Claude 3.5 Sonnet (Anthropic)</option>
              <option value="ollama-llama3">Local Ollama LLaMA 3 (Self-Hosted)</option>
            </select>
          </div>
        </div>

        {/* Sliders */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2 text-xs">
          <div>
            <div className="flex justify-between font-semibold text-zinc-700 mb-1">
              <span>Temperature (Creativity)</span>
              <span className="font-mono text-indigo-600 font-bold">{temperature}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full accent-indigo-600 cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between font-semibold text-zinc-700 mb-1">
              <span>Retrieval Match Threshold</span>
              <span className="font-mono text-indigo-600 font-bold">{searchThreshold}</span>
            </div>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={searchThreshold}
              onChange={(e) => setSearchThreshold(parseFloat(e.target.value))}
              className="w-full accent-indigo-600 cursor-pointer"
            />
          </div>
        </div>

        {/* System Prompt Customizer */}
        <div className="text-xs pt-2">
          <label className="block font-semibold text-zinc-700 mb-1">AI Shopping Persona & System Prompt</label>
          <textarea
            rows={4}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="Custom tone, styling guidelines, and store voice..."
            className="w-full px-3.5 py-2 rounded-xl border border-zinc-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 font-mono text-[11px]"
          />
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center justify-between">
        {savedSuccess ? (
          <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-600">
            <CheckCircle2 className="w-4 h-4" /> Settings updated successfully!
          </div>
        ) : (
          <div />
        )}

        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-xs transition active:scale-95"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </form>
  );
}
