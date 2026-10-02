'use client';

import React, { useState } from 'react';
import {
  Search,
  Sparkles,
  ArrowRight,
  Filter,
  RefreshCw,
  Layers,
  ChevronRight,
  Tag
} from 'lucide-react';
import { AIModeApiClient } from '../services/ai-mode-api';
import { AIModeProduct, AIModeSearchResponse } from '../types';
import AIModeProductCard from './AIModeProductCard';
import AIModeComparisonView from './AIModeComparisonView';

export default function AIModeSearchPlayground() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AIModeSearchResponse | null>(null);
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [comparisonData, setComparisonData] = useState<any>(null);
  const [loadingCompare, setLoadingCompare] = useState(false);

  const sampleQueries = [
    'Lightweight running jackets under ₹2,500',
    'Show UPF 50+ Sunscreen Jackets',
    'Travel joggers with zipper pockets',
    'Compare top athletic hoodies',
    'Cheapest moisture-wicking shirts'
  ];

  const handleSearch = async (queryText?: string, page = 1) => {
    const q = queryText || query;
    if (!q.trim()) return;
    setLoading(true);
    try {
      const res = await AIModeApiClient.search(q, page);
      if (page > 1 && result) {
        setResult({
          ...res,
          products: [...result.products, ...res.products]
        });
      } else {
        setResult(res);
      }
    } catch (err: any) {
      alert(`Search error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleCompare = (id: string) => {
    if (selectedForCompare.includes(id)) {
      setSelectedForCompare(selectedForCompare.filter((i) => i !== id));
    } else {
      if (selectedForCompare.length >= 4) {
        alert('You can compare up to 4 items simultaneously.');
        return;
      }
      setSelectedForCompare([...selectedForCompare, id]);
    }
  };

  const handleRunComparison = async () => {
    if (selectedForCompare.length < 2) {
      alert('Please select at least 2 products to compare.');
      return;
    }
    setLoadingCompare(true);
    try {
      const res = await AIModeApiClient.compare(selectedForCompare);
      setComparisonData(res);
    } catch (err: any) {
      alert(`Comparison error: ${err.message}`);
    } finally {
      setLoadingCompare(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Input Bar */}
      <div className="bg-white p-6 rounded-3xl border border-zinc-200 shadow-xs space-y-4">
        <div>
          <h2 className="text-base font-bold text-zinc-900">AI Natural-Language Search Studio</h2>
          <p className="text-xs text-zinc-500 mt-0.5">
            Test any unstructured conversational prompt. The AI will formulate a search plan and retrieve relevant items.
          </p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
          className="relative flex items-center"
        >
          <Search className="w-5 h-5 text-zinc-400 absolute left-4 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask anything, e.g. 'I need breathable travel shorts under ₹1500 in blue color'..."
            className="w-full pl-12 pr-28 py-3.5 text-xs sm:text-sm bg-zinc-50 rounded-2xl border border-zinc-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:bg-white transition"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="absolute right-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-300 text-white text-xs font-bold rounded-xl shadow-xs transition active:scale-95"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Search'}
          </button>
        </form>

        {/* Suggestion Chips */}
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pt-1">
          <span className="text-[11px] font-semibold text-zinc-400 shrink-0">Try asking:</span>
          {sampleQueries.map((sq, i) => (
            <button
              key={i}
              type="button"
              onClick={() => {
                setQuery(sq);
                handleSearch(sq);
              }}
              className="px-2.5 py-1 text-[11px] font-medium bg-zinc-100 hover:bg-indigo-50 hover:text-indigo-600 text-zinc-700 rounded-lg whitespace-nowrap transition"
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Comparison Action Bar */}
      {selectedForCompare.length > 0 && (
        <div className="p-4 bg-indigo-900 text-white rounded-2xl flex items-center justify-between shadow-lg animate-in slide-in-from-top-2">
          <div className="flex items-center gap-2 text-xs font-semibold">
            <Layers className="w-4 h-4 text-indigo-400" />
            {selectedForCompare.length} product{selectedForCompare.length > 1 ? 's' : ''} selected for comparison
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSelectedForCompare([])}
              className="px-3 py-1.5 text-xs text-zinc-300 hover:text-white transition"
            >
              Clear
            </button>
            <button
              onClick={handleRunComparison}
              disabled={loadingCompare || selectedForCompare.length < 2}
              className="px-4 py-1.5 bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-xs transition"
            >
              {loadingCompare ? 'Analyzing Specs...' : 'Compare Selected Products'}
            </button>
          </div>
        </div>
      )}

      {/* Active Comparison Matrix Display */}
      {comparisonData && (
        <AIModeComparisonView
          products={comparisonData.products}
          comparisonTable={comparisonData.comparison_table}
          aiSummary={comparisonData.ai_summary}
          verdict={comparisonData.verdict}
          bestFor={comparisonData.best_for}
          onClose={() => setComparisonData(null)}
        />
      )}

      {/* Search Plan & Diagnostic Inspector */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            {/* AI Summary Banner */}
            <div className="p-4 bg-white rounded-2xl border border-zinc-200 shadow-xs flex items-start gap-3">
              <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 shrink-0">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <div className="text-xs font-bold text-zinc-900">AI Query Synthesis</div>
                <p className="text-xs text-zinc-600 mt-0.5 leading-relaxed">{result.ai_summary}</p>
                <div className="text-[11px] text-zinc-400 mt-1">
                  Showing {result.products.length} of {result.total_matches} matched catalog items
                </div>
              </div>
            </div>

            {/* Product Cards Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {result.products.map((prod) => (
                <AIModeProductCard
                  key={prod.id}
                  product={prod}
                  onAddToCart={() => alert(`Added ${prod.title} to cart!`)}
                  onSelectForCompare={toggleCompare}
                  isCompareSelected={selectedForCompare.includes(prod.id)}
                />
              ))}
            </div>

            {/* Pagination Button */}
            {result.has_more && (
              <div className="text-center pt-2">
                <button
                  onClick={() => handleSearch(result.query, result.page + 1)}
                  disabled={loading}
                  className="px-6 py-2.5 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold rounded-xl shadow-xs transition"
                >
                  {loading ? 'Loading more...' : 'Show More Matching Products'}
                </button>
              </div>
            )}
          </div>

          {/* Search Plan Diagnostic Box */}
          <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-xs space-y-4 h-fit">
            <div className="flex items-center gap-2 text-xs font-bold text-zinc-900">
              <Filter className="w-4 h-4 text-indigo-600" />
              Dynamic NLU Search Plan
            </div>

            <div className="space-y-2 text-xs">
              <div className="p-2.5 bg-zinc-50 rounded-xl">
                <div className="text-[10px] uppercase font-semibold text-zinc-400">Classified Intent</div>
                <div className="font-bold text-indigo-600">{result.search_plan.intent}</div>
              </div>

              <div className="p-2.5 bg-zinc-50 rounded-xl">
                <div className="text-[10px] uppercase font-semibold text-zinc-400">Cleaned Search Tokens</div>
                <div className="font-mono text-zinc-800 font-semibold">{result.search_plan.clean_query || '(none)'}</div>
              </div>

              <div className="p-2.5 bg-zinc-50 rounded-xl">
                <div className="text-[10px] uppercase font-semibold text-zinc-400">Price Constraints</div>
                <div className="font-semibold text-zinc-800">
                  {result.search_plan.price_max ? `Max: ₹${result.search_plan.price_max}` : 'No Max'} •{' '}
                  {result.search_plan.price_min ? `Min: ₹${result.search_plan.price_min}` : 'No Min'}
                </div>
              </div>

              <div className="p-2.5 bg-zinc-50 rounded-xl">
                <div className="text-[10px] uppercase font-semibold text-zinc-400">Sorting Strategy</div>
                <div className="font-semibold text-zinc-800">{result.search_plan.sort_by || 'RELEVANCE'}</div>
              </div>
            </div>

            {result.suggestions && result.suggestions.length > 0 && (
              <div className="pt-2 border-t border-zinc-100">
                <div className="text-[11px] font-bold text-zinc-700 mb-2">Follow-up Queries</div>
                <div className="space-y-1.5">
                  {result.suggestions.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => {
                        setQuery(s);
                        handleSearch(s);
                      }}
                      className="w-full text-left p-2 text-xs text-zinc-700 hover:text-indigo-600 hover:bg-indigo-50/50 rounded-lg flex items-center justify-between transition"
                    >
                      <span className="truncate">{s}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
