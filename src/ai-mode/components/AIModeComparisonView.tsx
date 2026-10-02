'use client';

import React from 'react';
import { Check, X, Sparkles, ShoppingBag } from 'lucide-react';
import { AIModeProduct } from '../types';

interface AIModeComparisonViewProps {
  products: AIModeProduct[];
  comparisonTable: Array<Record<string, any>>;
  aiSummary?: string;
  verdict?: string;
  bestFor?: Record<string, string>;
  onClose?: () => void;
  onAddToCart?: (productId: string) => void;
}

export default function AIModeComparisonView({
  products,
  comparisonTable,
  aiSummary,
  verdict,
  bestFor = {},
  onClose,
  onAddToCart
}: AIModeComparisonViewProps) {
  if (!products || products.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl border border-zinc-200 shadow-xl overflow-hidden my-4">
      {/* Header */}
      <div className="p-4 sm:p-6 bg-gradient-to-r from-indigo-900 to-zinc-900 text-white flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            <h3 className="text-base sm:text-lg font-bold">AI Product Comparison Matrix</h3>
          </div>
          <p className="text-xs text-indigo-200 mt-0.5">Authoritative side-by-side specifications</p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white transition"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* AI Summary Banner */}
      {aiSummary && (
        <div className="p-4 bg-indigo-50/70 border-b border-indigo-100 flex items-start gap-3">
          <div className="p-1.5 rounded-lg bg-indigo-100 text-indigo-700 shrink-0 mt-0.5">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-semibold text-indigo-900">AI Analysis & Verdict</div>
            <p className="text-xs text-indigo-700 leading-relaxed mt-0.5">{aiSummary}</p>
            {verdict && <p className="text-xs font-medium text-indigo-900 mt-1">💡 {verdict}</p>}
          </div>
        </div>
      )}

      {/* Product Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 p-4 border-b border-zinc-200 bg-zinc-50">
        {products.map((p) => (
          <div key={p.id} className="bg-white rounded-xl p-3 border border-zinc-200/80 shadow-xs flex flex-col justify-between">
            <div>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={p.images?.[0] || 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=400'}
                alt={p.title}
                className="w-full h-28 object-cover rounded-lg mb-2"
              />
              <div className="text-[10px] uppercase font-bold text-indigo-600 tracking-wider">{p.category}</div>
              <h4 className="text-xs font-bold text-zinc-900 line-clamp-2" title={p.title}>{p.title}</h4>
              <div className="text-sm font-extrabold text-zinc-900 mt-1">
                {p.currency} {p.price.toLocaleString()}
              </div>

              {bestFor[p.id] && (
                <div className="mt-2 px-2 py-1 text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200 rounded-md">
                  ★ {bestFor[p.id]}
                </div>
              )}
            </div>

            {onAddToCart && (
              <button
                onClick={() => onAddToCart(p.id)}
                className="mt-3 w-full py-1.5 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition"
              >
                <ShoppingBag className="w-3.5 h-3.5" />
                Add to Cart
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Comparison Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="bg-zinc-100 text-zinc-600 font-semibold border-b border-zinc-200">
              <th className="py-2.5 px-4 w-40">Attribute</th>
              {products.map((p) => (
                <th key={p.id} className="py-2.5 px-4 font-bold text-zinc-900">
                  {p.title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-200/60">
            {comparisonTable.map((row, i) => (
              <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-zinc-50/50'}>
                <td className="py-2.5 px-4 font-semibold text-zinc-700 bg-zinc-50/80">
                  {row.feature}
                </td>
                {products.map((p) => {
                  const val = row[p.title] ?? 'Information not available';
                  const isMissing = val === 'Information not available';
                  return (
                    <td
                      key={p.id}
                      className={`py-2.5 px-4 ${
                        isMissing ? 'text-zinc-400 italic' : 'text-zinc-800 font-medium'
                      }`}
                    >
                      {val}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
