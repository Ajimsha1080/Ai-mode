'use client';

import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  Plus,
  RefreshCw,
  Trash2,
  Globe,
  FileText,
  HelpCircle,
  CheckCircle2,
  AlertCircle,
  Upload,
  Link as LinkIcon,
  ExternalLink
} from 'lucide-react';
import { AIModeApiClient } from '../services/ai-mode-api';
import { AIModeKnowledgeSource } from '../types';

export default function AIModeKnowledge() {
  const [sources, setSources] = useState<AIModeKnowledgeSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newType, setNewType] = useState<'URL_CRAWLER' | 'FILE_UPLOAD' | 'FAQ'>('URL_CRAWLER');
  const [newName, setNewName] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const [newContent, setNewContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSources = async () => {
    try {
      setLoading(true);
      const data = await AIModeApiClient.getKnowledgeSources();
      setSources(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  const handleSync = async (sourceId: string) => {
    setSyncingId(sourceId);
    try {
      await AIModeApiClient.syncKnowledgeSource(sourceId);
      await fetchSources();
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setSyncingId(null);
    }
  };

  const handleDelete = async (sourceId: string) => {
    if (!confirm('Are you sure you want to remove this knowledge source?')) return;
    try {
      await AIModeApiClient.deleteKnowledgeSource(sourceId);
      await fetchSources();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName) return;
    setSubmitting(true);
    setError(null);

    try {
      const config = newType === 'URL_CRAWLER' ? { url: newUrl } : { format: 'text' };
      await AIModeApiClient.createKnowledgeSource({
        name: newName,
        source_type: newType,
        config,
        content: newContent
      });
      setShowAddModal(false);
      setNewName('');
      setNewUrl('');
      setNewContent('');
      await fetchSources();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-zinc-200 shadow-xs">
        <div>
          <h2 className="text-lg font-bold text-zinc-900">Knowledge & Store Context</h2>
          <p className="text-xs text-zinc-500 mt-1">
            Connect external web pages, upload manuals, or define store policies for AI Mode.
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-xs transition active:scale-95"
        >
          <Plus className="w-4 h-4" />
          Add Knowledge Source
        </button>
      </div>

      {/* Sources Grid */}
      {loading ? (
        <div className="p-12 text-center text-zinc-400 bg-white rounded-2xl border border-zinc-200">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-600" />
          <p className="text-xs">Loading knowledge sources...</p>
        </div>
      ) : sources.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-2xl border border-dashed border-zinc-300">
          <BookOpen className="w-10 h-10 text-zinc-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-zinc-800">No Knowledge Sources Added Yet</h3>
          <p className="text-xs text-zinc-500 mt-1 max-w-sm mx-auto">
            Add a website URL crawler, upload policy documents, or enter FAQs to ground AI Mode.
          </p>
          <button
            onClick={() => setShowAddModal(true)}
            className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-2 bg-zinc-900 text-white text-xs font-semibold rounded-xl hover:bg-zinc-800 transition"
          >
            <Plus className="w-3.5 h-3.5" />
            Add First Source
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sources.map((src) => {
            const isSyncing = syncingId === src.id;
            return (
              <div
                key={src.id}
                className="bg-white rounded-2xl border border-zinc-200 p-5 shadow-xs flex flex-col justify-between hover:border-indigo-300 transition"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="p-2 rounded-xl bg-indigo-50 text-indigo-600">
                      {src.source_type === 'URL_CRAWLER' ? (
                        <Globe className="w-4 h-4" />
                      ) : src.source_type === 'FILE_UPLOAD' ? (
                        <FileText className="w-4 h-4" />
                      ) : (
                        <HelpCircle className="w-4 h-4" />
                      )}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        src.status === 'READY'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : src.status === 'SYNCING'
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}
                    >
                      {src.status === 'READY' && <CheckCircle2 className="w-3 h-3 text-emerald-500" />}
                      {src.status === 'SYNCING' && <RefreshCw className="w-3 h-3 animate-spin text-amber-500" />}
                      {src.status === 'ERROR' && <AlertCircle className="w-3 h-3 text-rose-500" />}
                      {src.status}
                    </span>
                  </div>

                  <h3 className="font-bold text-zinc-900 text-sm mt-3">{src.name}</h3>
                  {src.config?.url && (
                    <a
                      href={src.config.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[11px] text-indigo-600 hover:underline flex items-center gap-1 mt-0.5 truncate"
                    >
                      <LinkIcon className="w-3 h-3 shrink-0" />
                      <span className="truncate">{src.config.url}</span>
                    </a>
                  )}

                  <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-zinc-100 text-xs">
                    <div>
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Documents</div>
                      <div className="font-bold text-zinc-800">{src.document_count}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Vector Chunks</div>
                      <div className="font-bold text-zinc-800">{src.chunk_count}</div>
                    </div>
                  </div>

                  {src.error_message && (
                    <div className="mt-3 p-2 bg-rose-50 border border-rose-200 rounded-lg text-[11px] text-rose-700">
                      {src.error_message}
                    </div>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-zinc-100 flex items-center justify-between text-xs">
                  <span className="text-[10px] text-zinc-400">
                    Synced: {src.last_synced_at ? new Date(src.last_synced_at).toLocaleTimeString() : 'Never'}
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleSync(src.id)}
                      disabled={isSyncing}
                      className="p-1.5 text-zinc-400 hover:text-indigo-600 hover:bg-zinc-100 rounded-lg transition"
                      title="Re-sync"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin text-indigo-600' : ''}`} />
                    </button>
                    <button
                      onClick={() => handleDelete(src.id)}
                      className="p-1.5 text-zinc-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                      title="Delete source"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Knowledge Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl border border-zinc-200 shadow-2xl max-w-lg w-full p-6 animate-in fade-in duration-200">
            <h3 className="text-base font-bold text-zinc-900">Add AI Mode Knowledge Source</h3>
            <p className="text-xs text-zinc-500 mt-0.5">
              Choose a source type to ground AI search and conversation in your store data.
            </p>

            <form onSubmit={handleCreate} className="mt-4 space-y-4">
              {/* Type Switcher */}
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setNewType('URL_CRAWLER')}
                  className={`p-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition ${
                    newType === 'URL_CRAWLER'
                      ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                      : 'border-zinc-200 hover:bg-zinc-50 text-zinc-600'
                  }`}
                >
                  <Globe className="w-4 h-4" />
                  Website URL
                </button>
                <button
                  type="button"
                  onClick={() => setNewType('FILE_UPLOAD')}
                  className={`p-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition ${
                    newType === 'FILE_UPLOAD'
                      ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                      : 'border-zinc-200 hover:bg-zinc-50 text-zinc-600'
                  }`}
                >
                  <Upload className="w-4 h-4" />
                  File Upload
                </button>
                <button
                  type="button"
                  onClick={() => setNewType('FAQ')}
                  className={`p-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition ${
                    newType === 'FAQ'
                      ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                      : 'border-zinc-200 hover:bg-zinc-50 text-zinc-600'
                  }`}
                >
                  <HelpCircle className="w-4 h-4" />
                  FAQs / Policy
                </button>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-700 mb-1">Source Name</label>
                <input
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Return & Exchange Policy or Store Homepage"
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-zinc-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              {newType === 'URL_CRAWLER' && (
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 mb-1">Website URL to Crawl</label>
                  <input
                    type="url"
                    required
                    value={newUrl}
                    onChange={(e) => setNewUrl(e.target.value)}
                    placeholder="https://example.com/about-or-products"
                    className="w-full px-3.5 py-2 text-xs rounded-xl border border-zinc-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                  <p className="text-[11px] text-zinc-400 mt-1">
                    AI Mode crawler will extract authoritative text, headings, and product boundaries.
                  </p>
                </div>
              )}

              {newType !== 'URL_CRAWLER' && (
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 mb-1">Knowledge Content / Text</label>
                  <textarea
                    rows={4}
                    required
                    value={newContent}
                    onChange={(e) => setNewContent(e.target.value)}
                    placeholder="Enter policy terms, sizing details, shipping timelines, or FAQs here..."
                    className="w-full px-3.5 py-2 text-xs rounded-xl border border-zinc-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              )}

              {error && (
                <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700">
                  {error}
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-zinc-600 hover:bg-zinc-100 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-xs transition"
                >
                  {submitting ? 'Indexing...' : 'Save & Ingest'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
