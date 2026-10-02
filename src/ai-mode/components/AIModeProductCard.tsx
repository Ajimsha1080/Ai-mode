'use client';

import React, { useState } from 'react';
import { ShoppingBag, Check, ExternalLink, Sparkles } from 'lucide-react';
import { AIModeProduct } from '../types';

interface AIModeProductCardProps {
  product: AIModeProduct;
  onAddToCart?: (productId: string) => Promise<void> | void;
  onSelectForCompare?: (productId: string) => void;
  isCompareSelected?: boolean;
}

export default function AIModeProductCard({
  product,
  onAddToCart,
  onSelectForCompare,
  isCompareSelected = false
}: AIModeProductCardProps) {
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState(false);

  const handleAdd = async () => {
    if (!onAddToCart || adding) return;
    setAdding(true);
    try {
      await onAddToCart(product.id);
      setAdded(true);
      setTimeout(() => setAdded(false), 2000);
    } finally {
      setAdding(false);
    }
  };

  const imageSrc = product.images?.[0] || 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=500&auto=format&fit=crop&q=60';

  return (
    <div className="group relative bg-white rounded-2xl border border-zinc-200/80 shadow-xs hover:shadow-lg transition-all duration-300 flex flex-col overflow-hidden">
      {/* Product Image & Badges */}
      <div className="relative aspect-square w-full bg-zinc-100 overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={imageSrc}
          alt={product.title}
          className="h-full w-full object-cover object-center group-hover:scale-105 transition-transform duration-500"
          loading="lazy"
        />

        {/* Stock & Score Badges */}
        <div className="absolute top-2.5 left-2.5 flex flex-col gap-1">
          {product.in_stock ? (
            <span className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-500 text-white rounded-full shadow-xs">
              In Stock
            </span>
          ) : (
            <span className="px-2 py-0.5 text-[10px] font-semibold bg-rose-500 text-white rounded-full shadow-xs">
              Out of Stock
            </span>
          )}
          {product.score !== undefined && product.score !== null && (
            <span className="px-2 py-0.5 text-[10px] font-medium bg-zinc-900/80 backdrop-blur-xs text-white rounded-full flex items-center gap-1">
              <Sparkles className="w-2.5 h-2.5 text-amber-400" />
              {Math.round(product.score * 100)}% Match
            </span>
          )}
        </div>

        {onSelectForCompare && (
          <button
            onClick={() => onSelectForCompare(product.id)}
            className={`absolute top-2.5 right-2.5 px-2 py-1 text-[11px] font-medium rounded-lg backdrop-blur-xs transition-colors shadow-xs ${
              isCompareSelected
                ? 'bg-indigo-600 text-white'
                : 'bg-white/90 text-zinc-700 hover:bg-white'
            }`}
          >
            {isCompareSelected ? 'Selected' : '+ Compare'}
          </button>
        )}
      </div>

      {/* Content Body */}
      <div className="p-4 flex-1 flex flex-col justify-between">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-indigo-600 mb-1">
            {product.category || 'General'}
          </div>
          <h3 className="font-semibold text-zinc-900 text-sm leading-snug line-clamp-2" title={product.title}>
            {product.title}
          </h3>

          {product.description && (
            <p className="text-xs text-zinc-500 mt-1 line-clamp-2">
              {product.description}
            </p>
          )}

          {/* Highlights */}
          {product.highlights && product.highlights.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2.5">
              {product.highlights.slice(0, 2).map((h, i) => (
                <span key={i} className="px-1.5 py-0.5 text-[10px] bg-zinc-100 text-zinc-600 rounded-md">
                  {h}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Pricing & Add-to-Cart Action */}
        <div className="mt-4 pt-3 border-t border-zinc-100 flex items-center justify-between">
          <div>
            <div className="text-base font-bold text-zinc-900">
              {product.currency} {product.price.toLocaleString()}
            </div>
            {product.compare_at_price && product.compare_at_price > product.price && (
              <div className="text-xs text-zinc-400 line-through">
                {product.currency} {product.compare_at_price.toLocaleString()}
              </div>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            {product.source_url && (
              <a
                href={product.source_url}
                target="_blank"
                rel="noreferrer"
                className="p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-xl transition"
                title="View Product Link"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            )}

            {onAddToCart && (
              <button
                onClick={handleAdd}
                disabled={!product.in_stock || adding}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-semibold shadow-xs transition-all ${
                  added
                    ? 'bg-emerald-600 text-white'
                    : !product.in_stock
                    ? 'bg-zinc-100 text-zinc-400 cursor-not-allowed'
                    : 'bg-zinc-900 hover:bg-zinc-800 text-white active:scale-95'
                }`}
              >
                {added ? (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    Added
                  </>
                ) : (
                  <>
                    <ShoppingBag className="w-3.5 h-3.5" />
                    {adding ? '...' : 'Add'}
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
