'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  Bot,
  User,
  ShoppingBag,
  RotateCcw,
  RefreshCw,
  Layers
} from 'lucide-react';
import { AIModeApiClient } from '../services/ai-mode-api';
import AIModeProductCard from './AIModeProductCard';
import AIModeComparisonView from './AIModeComparisonView';

interface Message {
  id: string;
  sender: 'USER' | 'ASSISTANT';
  content: string;
  products?: any[];
  comparison_matrix?: any;
  suggestions?: string[];
}

export default function AIModePreview() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init',
      sender: 'ASSISTANT',
      content: "Hello! 👋 I'm your AI Mode shopping concierge. What can I help you find in our catalog today?",
      suggestions: [
        'Show UPF 50+ Sunscreen Jackets',
        'Find products under ₹1,000',
        'What is your return policy?',
        'Compare athletic joggers'
      ]
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [cartCount, setCartCount] = useState(0);
  const [activeComparison, setActiveComparison] = useState<any>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (textToSend?: string) => {
    const text = textToSend || input;
    if (!text.trim() || loading) return;

    const userMsg: Message = {
      id: `u_${Date.now()}`,
      sender: 'USER',
      content: text
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput('');
    setLoading(true);

    try {
      const res = await AIModeApiClient.chat(text, conversationId || undefined, 'PREVIEW');
      if (res.conversation_id) setConversationId(res.conversation_id);

      const assistantMsg: Message = {
        id: res.message_id || `a_${Date.now()}`,
        sender: 'ASSISTANT',
        content: res.response,
        products: res.products,
        comparison_matrix: res.comparison_matrix,
        suggestions: res.suggestions
      };

      setMessages((prev) => [...prev, assistantMsg]);
      if (res.comparison_matrix) {
        setActiveComparison(res.comparison_matrix);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          sender: 'ASSISTANT',
          content: `⚠️ Error: ${err.message}`
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCart = async (productId: string) => {
    setCartCount((c) => c + 1);
    await handleSend(`Add product ${productId} to cart`);
  };

  const resetSession = () => {
    setConversationId(null);
    setCartCount(0);
    setActiveComparison(null);
    setMessages([
      {
        id: 'init_reset',
        sender: 'ASSISTANT',
        content: "Session reset! What would you like to explore now?",
        suggestions: [
          'Show best selling items',
          'Search items under ₹1,500',
          'Check exchange policy'
        ]
      }
    ]);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex items-center justify-between bg-white p-4 sm:p-6 rounded-2xl border border-zinc-200 shadow-xs">
        <div>
          <h2 className="text-base font-bold text-zinc-900">AI Mode Live Preview Canvas</h2>
          <p className="text-xs text-zinc-500 mt-0.5">
            Test multi-turn natural language dialogue, real catalog retrieval, and cart actions in real time.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-100 rounded-xl text-xs font-semibold text-zinc-700">
            <ShoppingBag className="w-3.5 h-3.5 text-indigo-600" />
            Cart: {cartCount} items
          </div>
          <button
            onClick={resetSession}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100 rounded-xl transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset
          </button>
        </div>
      </div>

      {/* Comparison Modal if Active */}
      {activeComparison && (
        <AIModeComparisonView
          products={activeComparison.products}
          comparisonTable={activeComparison.comparison_table}
          aiSummary={activeComparison.ai_summary}
          verdict={activeComparison.verdict}
          bestFor={activeComparison.best_for}
          onClose={() => setActiveComparison(null)}
          onAddToCart={handleAddToCart}
        />
      )}

      {/* Chat Window */}
      <div className="bg-white rounded-3xl border border-zinc-200 shadow-xl overflow-hidden flex flex-col h-[650px]">
        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-zinc-50/50">
          {messages.map((m) => {
            const isAssistant = m.sender === 'ASSISTANT';
            return (
              <div
                key={m.id}
                className={`flex gap-3 max-w-3xl ${isAssistant ? '' : 'ml-auto justify-end'}`}
              >
                {isAssistant && (
                  <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-xs mt-1">
                    <Sparkles className="w-4 h-4" />
                  </div>
                )}

                <div className={`space-y-3 ${isAssistant ? 'w-full' : 'max-w-md'}`}>
                  {/* Bubble */}
                  <div
                    className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                      isAssistant
                        ? 'bg-white border border-zinc-200 text-zinc-800 shadow-xs'
                        : 'bg-zinc-900 text-white rounded-br-xs'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{m.content}</div>
                  </div>

                  {/* Product Cards Carousel / Grid */}
                  {m.products && m.products.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-1">
                      {m.products.map((p) => (
                        <AIModeProductCard
                          key={p.id}
                          product={p}
                          onAddToCart={handleAddToCart}
                        />
                      ))}
                    </div>
                  )}

                  {/* Suggestions Chips */}
                  {m.suggestions && m.suggestions.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {m.suggestions.map((s, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSend(s)}
                          className="px-3 py-1 bg-white hover:bg-indigo-50 text-indigo-700 border border-indigo-200/80 rounded-full text-xs font-medium transition shadow-2xs hover:scale-102 active:scale-98"
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {!isAssistant && (
                  <div className="w-8 h-8 rounded-full bg-zinc-900 text-white flex items-center justify-center shrink-0 shadow-xs mt-1">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}

          {loading && (
            <div className="flex gap-3 items-center text-xs text-zinc-400">
              <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center animate-pulse">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="p-3 bg-white rounded-2xl border border-zinc-200 shadow-2xs flex items-center gap-2">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                <span>AI Mode is formulating search plan & specs...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Chat Input Bar */}
        <div className="p-4 bg-white border-t border-zinc-200">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything, follow up on products, or request a comparison..."
              className="flex-1 px-4 py-3 text-xs sm:text-sm bg-zinc-50 border border-zinc-200 rounded-2xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:bg-white transition"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="p-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-200 text-white rounded-2xl shadow-xs transition active:scale-95"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
