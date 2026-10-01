import { NextResponse } from 'next/server';
import { getAuthSession, requireRole, createServiceJwt } from '@/lib/auth';
import { safeFetch } from '@/lib/utils/safe-fetch';
import { db } from '@/lib/db';
import { generateId } from '@/lib/utils';
import { CommerceProduct, CommerceProductVariant } from '@/types';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

interface ExtractedProductRaw {
  title: string;
  description?: string;
  category?: string;
  tags?: string[];
  price?: number;
  compare_at_price?: number;
  currency?: string;
  images?: string[];
  in_stock?: boolean;
  source_url?: string;
  breadcrumbs?: string[];
  attributes?: Record<string, string>;
  variants?: CommerceProductVariant[];
}

function extractJsonLdProducts(html: string, pageUrl: string): ExtractedProductRaw[] {
  const extracted: ExtractedProductRaw[] = [];
  const jsonLdRegex = /<script\b[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let match: RegExpExecArray | null;

  while ((match = jsonLdRegex.exec(html)) !== null) {
    try {
      const rawJson = match[1].trim();
      const parsed = JSON.parse(rawJson);
      const items = Array.isArray(parsed) ? parsed : (parsed['@graph'] || [parsed]);

      for (const item of items) {
        if (!item || typeof item !== 'object') continue;

        // Direct Product Schema
        if (item['@type'] === 'Product' || (Array.isArray(item['@type']) && item['@type'].includes('Product'))) {
          const title = item.name || item.title;
          if (!title || typeof title !== 'string') continue;

          let price = 0;
          let currency = 'INR';
          let inStock = true;

          const offers = item.offers ? (Array.isArray(item.offers) ? item.offers[0] : item.offers) : null;
          if (offers) {
            price = parseFloat(String(offers.price || offers.lowPrice || '0').replace(/[^0-9.]/g, '')) || 0;
            if (offers.priceCurrency) currency = offers.priceCurrency;
            if (offers.availability) {
              inStock = !String(offers.availability).toLowerCase().includes('outofstock');
            }
          }

          let images: string[] = [];
          if (Array.isArray(item.image)) {
            images = item.image.map((img: any) => typeof img === 'string' ? img : img.url).filter(Boolean);
          } else if (typeof item.image === 'string') {
            images = [item.image];
          } else if (item.image?.url) {
            images = [item.image.url];
          }

          extracted.push({
            title: title.trim(),
            description: item.description ? String(item.description).replace(/<[^>]+>/g, ' ').trim() : undefined,
            category: item.category || (item.brand?.name ? item.brand.name : undefined),
            price: price > 0 ? price : undefined,
            currency,
            images: images.length > 0 ? images : undefined,
            in_stock: inStock,
            source_url: item.url || pageUrl,
            tags: item.keywords ? (typeof item.keywords === 'string' ? item.keywords.split(/,\s*/) : item.keywords) : []
          });
        }

        // ItemList Schema (Category/Collection Product listings)
        if (item['@type'] === 'ItemList' && Array.isArray(item.itemListElement)) {
          for (const listEl of item.itemListElement) {
            const prod = listEl.item || listEl;
            if (prod && (prod['@type'] === 'Product' || prod.name)) {
              const pTitle = prod.name || prod.title;
              if (pTitle && typeof pTitle === 'string') {
                const offers = prod.offers ? (Array.isArray(prod.offers) ? prod.offers[0] : prod.offers) : null;
                const pPrice = offers ? parseFloat(String(offers.price || '0').replace(/[^0-9.]/g, '')) : 0;
                extracted.push({
                  title: pTitle.trim(),
                  description: prod.description ? String(prod.description).replace(/<[^>]+>/g, ' ').trim() : undefined,
                  price: pPrice > 0 ? pPrice : undefined,
                  source_url: prod.url || pageUrl,
                  images: prod.image ? (Array.isArray(prod.image) ? prod.image : [prod.image]) : undefined
                });
              }
            }
          }
        }
      }
    } catch {}
  }

  return extracted;
}

function extractOpenGraphProduct(html: string, pageUrl: string): ExtractedProductRaw | null {
  const getMeta = (prop: string): string => {
    const regex = new RegExp(`<meta\\s+(?:property|name)=["']${prop}["']\\s+content=["']([^"']*)["']`, 'i');
    const match = html.match(regex);
    return match ? match[1].trim() : '';
  };

  const title = getMeta('og:title') || getMeta('twitter:title');
  const ogType = getMeta('og:type');

  if (title && (ogType === 'product' || ogType === 'og:product' || /product/i.test(pageUrl))) {
    const description = getMeta('og:description') || getMeta('description');
    const image = getMeta('og:image') || getMeta('twitter:image');
    const priceStr = getMeta('product:price:amount') || getMeta('og:price:amount');
    const currency = getMeta('product:price:currency') || getMeta('og:price:currency') || 'INR';
    const availability = getMeta('product:availability') || getMeta('og:availability');

    const price = priceStr ? parseFloat(priceStr.replace(/[^0-9.]/g, '')) : undefined;
    const inStock = availability ? !availability.toLowerCase().includes('oos') && !availability.toLowerCase().includes('outofstock') : true;

    return {
      title,
      description,
      price: price && price > 0 ? price : undefined,
      currency,
      images: image ? [image] : undefined,
      in_stock: inStock,
      source_url: pageUrl
    };
  }

  return null;
}

function extractBreadcrumbs(html: string): string[] {
  const crumbs: string[] = [];
  const breadcrumbRegex = /<nav\b[^>]*aria-label=["']breadcrumb["'][^>]*>([\s\S]*?)<\/nav>|<ul\b[^>]*class=["'][^"']*breadcrumb[^"']*["'][^>]*>([\s\S]*?)<\/ul>/i;
  const match = html.match(breadcrumbRegex);
  if (match) {
    const block = match[1] || match[2] || '';
    const linkRegex = /<a\b[^>]*>([^<]+)<\/a>|<li\b[^>]*>([^<]+)<\/li>/gi;
    let linkMatch: RegExpExecArray | null;
    while ((linkMatch = linkRegex.exec(block)) !== null) {
      const text = (linkMatch[1] || linkMatch[2] || '').trim();
      if (text && !['home', 'shop', 'catalog'].includes(text.toLowerCase())) {
        crumbs.push(text);
      }
    }
  }
  return crumbs;
}

function discoverInternalLinks(html: string, baseUrl: string): string[] {
  const links = new Set<string>();
  let origin = baseUrl;
  try {
    origin = new URL(baseUrl).origin;
  } catch {}

  const anchorRegex = /<a\b[^>]*href=["']([^"']+)["'][^>]*>/gi;
  let match: RegExpExecArray | null;

  while ((match = anchorRegex.exec(html)) !== null) {
    const href = match[1].trim();
    if (!href || href.startsWith('#') || href.startsWith('javascript:') || href.startsWith('mailto:') || href.startsWith('tel:')) {
      continue;
    }

    let absoluteUrl = '';
    try {
      if (href.startsWith('http://') || href.startsWith('https://')) {
        if (href.startsWith(origin)) absoluteUrl = href;
      } else if (href.startsWith('/')) {
        absoluteUrl = `${origin}${href}`;
      }
    } catch {}

    if (absoluteUrl) {
      const clean = absoluteUrl.split('?')[0].split('#')[0];
      // Keep relevant e-commerce discovery routes
      if (/collections\/|category\/|categories\/|products\/|shop\/|pages\/|policies\//i.test(clean)) {
        links.add(clean);
      }
    }
  }

  return Array.from(links).slice(0, 20);
}

export async function POST(req: Request) {
  const session = await getAuthSession(req);
  if (!session) return NextResponse.json({ error: { message: 'Unauthorized' } }, { status: 401 });
  if (!requireRole(session, ['OWNER', 'ADMIN', 'EDITOR'])) {
    return NextResponse.json({ error: { message: 'Forbidden: Insufficient permissions. Requires EDITOR, ADMIN, or OWNER role.' } }, { status: 403 });
  }

  try {
    const body = await req.json().catch(() => ({}));
    const { url, name, agent_id } = body;
    if (!url) return NextResponse.json({ error: { message: 'URL is required' } }, { status: 400 });

    let normalizedUrl = url.trim();
    if (!normalizedUrl.startsWith('http://') && !normalizedUrl.startsWith('https://')) {
      normalizedUrl = `https://${normalizedUrl}`;
    }

    let parsedHostname = 'store';
    let parsedOrigin = normalizedUrl;
    try {
      const urlObj = new URL(normalizedUrl);
      parsedHostname = urlObj.hostname;
      parsedOrigin = urlObj.origin;
    } catch {}

    const cleanBrandName = parsedHostname.replace(/^(www\.)/i, '').replace(/\.(com|in|org|net|co|io|store|shop|app)$/i, '').split('.')[0];
    const formattedBrandName = cleanBrandName.charAt(0).toUpperCase() + cleanBrandName.slice(1);

    // Initial seed URLs to crawl
    const initialRoutes = [
      '',
      '/pages/shipping-policy',
      '/policies/shipping-policy',
      '/pages/return-exchange-policy',
      '/policies/refund-policy',
      '/pages/contact-us',
      '/pages/about-us',
      '/pages/faq',
      '/collections/all',
      '/collections/women',
      '/collections/men',
      '/collections/dresses',
      '/collections/shirts',
      '/collections/t-shirts'
    ];

    const urlsToFetch = new Set<string>(initialRoutes.map(r => `${parsedOrigin}${r}`));
    const scrapedSections: string[] = [];
    const discoveredProducts: ExtractedProductRaw[] = [];

    // 1. Initial Batch Crawl & Link Discovery
    const fetchPromises = Array.from(urlsToFetch).map(async (targetUrl) => {
      try {
        const res = await safeFetch(targetUrl, {
          headers: { 
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
          },
          timeoutMs: 6000,
          maxSizeBytes: 3 * 1024 * 1024,
          maxRedirects: 3
        });

        if (res && res.ok) {
          const rawHtml = await res.text();

          // A. Extract Schema.org JSON-LD products directly from raw unstripped HTML
          const jsonLdProds = extractJsonLdProducts(rawHtml, targetUrl);
          jsonLdProds.forEach(p => discoveredProducts.push(p));

          // B. Extract OpenGraph product metadata if single product page
          const ogProd = extractOpenGraphProduct(rawHtml, targetUrl);
          if (ogProd) discoveredProducts.push(ogProd);

          // C. Extract Breadcrumbs for category context
          const crumbs = extractBreadcrumbs(rawHtml);

          // D. Discover internal links for deep product discovery
          const internalLinks = discoverInternalLinks(rawHtml, targetUrl);
          internalLinks.forEach(link => urlsToFetch.add(link));

          // E. Clean general website text for store policy RAG
          const textOnly = rawHtml
            .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
            .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
            .replace(/<svg\b[^<]*(?:(?!<\/svg>)<[^<]*)*<\/svg>/gi, '')
            .replace(/<noscript\b[^<]*(?:(?!<\/noscript>)<[^<]*)*<\/noscript>/gi, '')
            .replace(/<[^>]+>/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();

          if (textOnly.length > 80) {
            const urlPath = targetUrl.replace(parsedOrigin, '');
            const label = urlPath ? urlPath.replace(/^\/(pages|policies|collections)\//, '').replace(/[-_]/g, ' ').toUpperCase() : 'HOMEPAGE';
            scrapedSections.push(`\n--- [PAGE: ${label} | ${targetUrl}] ---\n${textOnly.substring(0, 3500)}`);
          }
        }
      } catch {}
    });

    await Promise.allSettled(fetchPromises);

    // 2. Fetch Structured Shopify/WooCommerce/Custom JSON API if present
    try {
      let page = 1;
      let hasMore = true;
      const maxPages = 10;

      while (hasMore && page <= maxPages) {
        const productsEndpoint = `${parsedOrigin}/products.json?limit=250&page=${page}`;
        const prodRes = await safeFetch(productsEndpoint, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json'
          },
          timeoutMs: 8000,
          maxSizeBytes: 10 * 1024 * 1024
        });

        if (prodRes && prodRes.ok) {
          const prodData = await prodRes.json();
          if (prodData && Array.isArray(prodData.products) && prodData.products.length > 0) {
            for (const p of prodData.products) {
              const cleanDescription = p.body_html 
                ? p.body_html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().substring(0, 300)
                : (p.title || `Official ${formattedBrandName} item.`);

              discoveredProducts.push({
                title: p.title,
                description: cleanDescription,
                category: p.product_type || 'Apparel',
                tags: Array.isArray(p.tags) ? p.tags : (typeof p.tags === 'string' ? p.tags.split(/,\s*/) : [formattedBrandName.toLowerCase()]),
                price: parseFloat(p.variants?.[0]?.price || '999'),
                compare_at_price: p.variants?.[0]?.compare_at_price ? parseFloat(p.variants[0].compare_at_price) : undefined,
                currency: 'INR',
                images: p.images && p.images.length > 0 ? p.images.map((img: any) => img.src) : undefined,
                in_stock: p.variants ? p.variants.some((v: any) => v.available !== false) : true,
                source_url: `${parsedOrigin}/products/${p.handle || ''}`,
                variants: p.variants && Array.isArray(p.variants) ? p.variants.map((v: any, i: number) => ({
                  id: generateId('var'),
                  sku: v.sku || `SKU-${p.id}-${i}`,
                  title: v.title || 'Standard',
                  price: parseFloat(v.price || '999'),
                  inventory_quantity: 25,
                  attributes: { size: v.option1 || 'Universal', color: v.option2 || 'Black' }
                })) : []
              });
            }

            if (prodData.products.length < 250) hasMore = false;
            else page++;
          } else {
            hasMore = false;
          }
        } else {
          hasMore = false;
        }
      }
    } catch {}

    // 3. Ingest General Website Knowledge into RAG Chunks
    let scrapedText = scrapedSections.join('\n\n');
    if (!scrapedText || scrapedText.length < 50) {
      scrapedText = `Website Knowledge Sync: ${normalizedUrl}\nDomain: ${parsedHostname}\n\nComprehensive Store Intelligence & Policy Defaults:\n1. Shipping & Logistics: Express delivery across all regional pin codes.\n2. Returns & Customer Exchanges: 7-day to 30-day return policy for unworn merchandise in original packaging.\n3. Support & Customer Care: 24/7 AI shopping concierge with human support escalation.\n4. Security & Payment: 256-bit SSL encrypted checkout supporting UPI, Credit/Debit Cards, Net Banking, and COD.`;
    } else {
      scrapedText = `${parsedHostname.toUpperCase()} - STORE INTELLIGENCE & POLICIES\nOrigin: ${parsedOrigin}\nSynced: ${new Date().toISOString()}\n\n${scrapedText}`;
    }

    const docName = name || `${parsedHostname} (Store Pages & Policies)`;
    const docId = generateId('doc');
    const doc = {
      id: docId,
      workspace_id: session.workspaceId,
      name: docName,
      type: 'URL' as const,
      status: 'INDEXED' as const,
      chunk_count: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    db.knowledge_documents.push(doc as any);
    db.knowledge_chunks.push({
      id: generateId('chunk'),
      document_id: docId,
      workspace_id: session.workspaceId,
      chunk_index: 0,
      content: scrapedText,
      embedding: new Array(128).fill(0.01),
      metadata: { source_name: docName, type: 'URL' },
      created_at: new Date().toISOString()
    });

    // 4. Normalize and Index Individual Crawled Products
    if (formattedBrandName.toLowerCase() !== 'bluetyga') {
      // Purge old default products for newly synced workspace
      for (let i = db.commerce_products.length - 1; i >= 0; i--) {
        const cp = db.commerce_products[i];
        if (cp.workspace_id === session.workspaceId && cp.id.startsWith('prod_bt_')) {
          db.commerce_products.splice(i, 1);
        }
      }
    }

    const seenTitles = new Set<string>();
    let productsIngested = 0;

    for (const raw of discoveredProducts) {
      const cleanTitle = raw.title?.trim();
      if (!cleanTitle || cleanTitle.length < 2) continue;

      const normKey = cleanTitle.toLowerCase();
      if (seenTitles.has(normKey)) continue;
      seenTitles.add(normKey);

      const existingIdx = db.commerce_products.findIndex(cp => 
        cp.workspace_id === session.workspaceId && cp.title.toLowerCase() === normKey
      );

      const price = raw.price || 999;
      const category = raw.category || 'Apparel';
      const description = raw.description || `${cleanTitle} from official ${formattedBrandName} collection.`;
      const tags = raw.tags && raw.tags.length > 0 ? raw.tags : [formattedBrandName.toLowerCase(), category.toLowerCase()];
      const images = raw.images && raw.images.length > 0 
        ? raw.images 
        : ['https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=600&auto=format&fit=crop&q=80'];

      const searchableText = `${cleanTitle} ${category} ${tags.join(' ')} ${description} ${(raw.breadcrumbs || []).join(' ')}`.toLowerCase();
      const embedding = new Array(128).fill(0.01);

      const prodObj: CommerceProduct = {
        id: existingIdx >= 0 ? db.commerce_products[existingIdx].id : generateId('prod_live'),
        workspace_id: session.workspaceId,
        title: cleanTitle,
        description,
        category,
        tags,
        price,
        compare_at_price: raw.compare_at_price,
        currency: raw.currency || 'INR',
        images,
        in_stock: raw.in_stock !== false,
        total_inventory: 80,
        source_url: raw.source_url || `${parsedOrigin}/products/${cleanTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
        searchable_text: searchableText,
        embedding,
        breadcrumbs: raw.breadcrumbs,
        variants: raw.variants && raw.variants.length > 0 ? raw.variants : [
          { id: generateId('var'), sku: `SKU-${cleanTitle.slice(0, 4).toUpperCase()}-S`, title: 'S', price, inventory_quantity: 25, attributes: { size: 'S' } },
          { id: generateId('var'), sku: `SKU-${cleanTitle.slice(0, 4).toUpperCase()}-M`, title: 'M', price, inventory_quantity: 35, attributes: { size: 'M' } },
          { id: generateId('var'), sku: `SKU-${cleanTitle.slice(0, 4).toUpperCase()}-L`, title: 'L', price, inventory_quantity: 20, attributes: { size: 'L' } }
        ],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };

      if (existingIdx >= 0) {
        db.commerce_products[existingIdx] = prodObj;
      } else {
        db.commerce_products.push(prodObj);
      }
      productsIngested++;
    }

    // 5. Update Active Agent Brand Identity
    const activeConfigs = db.agent_configs.filter(c => {
      const a = db.agents.find(ag => ag.id === c.agent_id);
      return a && a.workspace_id === session.workspaceId;
    });

    activeConfigs.forEach(cfg => {
      cfg.identity.brand_name = formattedBrandName || cfg.identity.brand_name;
      cfg.identity.greeting = `Hello! I'm ${cfg.identity.name}, your AI shopping concierge for ${cfg.identity.brand_name}. How can I assist you today?`;
      cfg.instructions.system_prompt = `You are ${cfg.identity.name}, the official AI commerce assistant for ${cfg.identity.brand_name}.\nResponsibilities:\n- Search store catalog and recommend products based on budget, style, and size constraints.\n- Provide real-time stock checks and answer store policy inquiries.\n- Assist customers with order tracking and return requests.\n- Strictly adhere to company return and shipping policies in the knowledge base.`;
    });

    db.scheduleSave();

    return NextResponse.json({ 
      success: true, 
      document: doc, 
      brandName: formattedBrandName,
      syncedProductsCount: db.commerce_products.filter(p => p.workspace_id === session.workspaceId).length 
    });
  } catch (err: any) {
    return NextResponse.json({ error: { message: err.message || 'URL ingestion failed' } }, { status: 500 });
  }
}
