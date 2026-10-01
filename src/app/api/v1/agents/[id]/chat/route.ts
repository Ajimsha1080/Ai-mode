import { NextResponse } from 'next/server';
import { verifyApiKey } from '@/lib/auth';
import { runAgentCycle } from '@/lib/agent-runtime';
import { db } from '@/lib/db';

function resolveProductCards(responseText: string, userMessage: string, workspaceId: string, currentPayload?: any) {
  if (currentPayload?.type === 'PRODUCTS' && Array.isArray(currentPayload.data)) {
    return currentPayload;
  }

  const respLower = (responseText || '').toLowerCase();
  const catalog = db.commerce_products.filter(p => p.workspace_id === workspaceId);
  const matched: any[] = [];

  // Direct title matching with catalog products mentioned in response
  catalog.forEach(p => {
    const pTitle = p.title.toLowerCase();
    if (respLower.includes(pTitle)) {
      if (!matched.some(m => m.id === p.id)) matched.push(p);
    }
  });

  if (matched.length > 0) {
    const seenIds = new Set<string>();
    const seenTitles = new Set<string>();
    const uniqueMatched: any[] = [];
    for (const p of matched) {
      const pTitle = p.title?.trim().toLowerCase();
      if (!seenIds.has(p.id) && !seenTitles.has(pTitle)) {
        seenIds.add(p.id);
        seenTitles.add(pTitle);
        uniqueMatched.push(p);
      }
    }
    return {
      type: 'PRODUCTS',
      data: uniqueMatched.slice(0, 6)
    };
  }

  return currentPayload || null;
}

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

export async function POST(req: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const authHeader = req.headers.get('Authorization') || req.headers.get('authorization') || '';
  const origin = req.headers.get('Origin') || req.headers.get('origin') || req.headers.get('referer') || '';

  let workspaceId: string | null = null;
  let isPublicDeployment = false;

  // 1. Check for Bearer API Key or Public Deployment Token
  if (authHeader.startsWith('Bearer ')) {
    const token = authHeader.substring(7).trim();

    if (token.startsWith('pk_live_') || token.startsWith('dep_')) {
      const dep = db.deployments.find(d => (d.public_key === token || d.id === token) && d.status === 'ACTIVE');
      if (dep) {
        if (dep.allowed_domains && !dep.allowed_domains.includes('*')) {
          const originHost = origin.replace(/^https?:\/\//, '').split('/')[0];
          const matched = dep.allowed_domains.some(domain => {
            if (domain.startsWith('*.')) {
              const root = domain.slice(2);
              return originHost.endsWith(root);
            }
            return originHost === domain || domain === '*';
          });
          if (!matched && origin) {
            return NextResponse.json({
              error: { code: 'FORBIDDEN_ORIGIN', message: `Origin '${origin}' is not authorized for this deployment widget.` }
            }, { status: 403 });
          }
        }
        workspaceId = dep.workspace_id;
        isPublicDeployment = true;
      }
    } else {
      const authResult = await verifyApiKey(token);
      if (authResult) {
        workspaceId = authResult.workspaceId;
      }
    }
  }

  if (!workspaceId) {
    return NextResponse.json({
      error: { code: 'UNAUTHORIZED', message: 'Valid Bearer API Key or Deployment Key required.' }
    }, { status: 401 });
  }

  try {
    const body = await req.json();
    const { message, conversation_id, customer_identifier, stream } = body;
    if (!message) {
      return NextResponse.json({ error: { code: 'INVALID_REQUEST', message: 'Field "message" is required.' } }, { status: 400 });
    }

    // 1. Forward request to Python FastAPI single backend of record
    try {
      const pyUrl = stream
        ? `${PYTHON_BACKEND_URL}/api/v1/agents/${id}/chat/stream`
        : `${PYTHON_BACKEND_URL}/api/v1/agents/${id}/chat`;

      const pyRes = await fetch(pyUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': authHeader,
          'Origin': origin
        },
        body: JSON.stringify({
          message,
          conversation_id,
          workspace_id: workspaceId
        }),
        signal: AbortSignal.timeout(10000)
      });

      if (pyRes.ok) {
        if (stream && pyRes.body) {
          return new Response(pyRes.body, {
            headers: {
              'Content-Type': 'text/event-stream',
              'Cache-Control': 'no-cache',
              'Connection': 'keep-alive'
            }
          });
        }

        const pyData = await pyRes.json();
        const finalPayload = resolveProductCards(pyData.response || '', message, workspaceId, pyData.interactive_payload);
        const pagination = finalPayload?.pagination || pyData.interactive_payload?.pagination || pyData.metadata?.pagination;

        return NextResponse.json({
          conversation_id: pyData.conversation_id || conversation_id,
          message_id: pyData.message_id || 'msg_py_' + Math.random().toString(36).substring(2, 9),
          response: pyData.response,
          interactive_payload: finalPayload,
          metadata: {
            products: finalPayload?.type === 'PRODUCTS' ? finalPayload.data : undefined,
            order: finalPayload?.type === 'ORDER_TRACKING' ? finalPayload.data : undefined,
            pagination: pagination || undefined,
          },
          trace: {
            latency_ms: pyData.trace?.duration_ms || pyData.trace?.latency_ms || 100,
            tokens_used: pyData.trace?.tokens_used || {},
            tools_called: (pyData.trace?.tool_executions || []).map((t: any) => t.tool_name)
          }
        });
      }
    } catch (pyErr) {
      // Fall through to embedded runtime if FastAPI process is restarting in dev
    }

    // 2. Embedded Runtime Execution Fallback
    const result = await runAgentCycle({
      agent_id: id,
      workspace_id: workspaceId,
      user_message: message,
      conversation_id,
      customer_identifier: customer_identifier || (isPublicDeployment ? 'anonymous_shopper' : 'api_client'),
      channel: isPublicDeployment ? 'WEBSITE' : 'API'
    });

    const finalPayload = resolveProductCards(result.response_text || '', message, workspaceId, result.interactive_payload);
    const pagination = finalPayload?.pagination || result.interactive_payload?.pagination || result.metadata?.pagination;

    return NextResponse.json({
      conversation_id: result.conversation_id,
      message_id: result.message_id,
      response: result.response_text,
      interactive_payload: finalPayload,
      metadata: {
        products: finalPayload?.type === 'PRODUCTS' ? finalPayload.data : undefined,
        order: finalPayload?.type === 'ORDER_TRACKING' ? finalPayload.data : undefined,
        pagination: pagination || undefined,
      },
      trace: {
        latency_ms: result.trace.latency_ms,
        tokens_used: result.trace.tokens_used,
        tools_called: result.trace.tool_executions.map(t => t.tool_name)
      }
    });
  } catch (err: any) {
    return NextResponse.json({ error: { code: 'RUNTIME_ERROR', message: err.message || 'Execution failed.' } }, { status: 500 });
  }
}
