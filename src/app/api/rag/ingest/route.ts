import { NextResponse } from 'next/server';
import { getAuthSession, requireRole, createServiceJwt } from '@/lib/auth';
import { enforceQuota } from '@/lib/billing/limits';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

export async function POST(req: Request) {
  const session = await getAuthSession(req);
  if (!session) return NextResponse.json({ error: { message: 'Unauthorized' } }, { status: 401 });

  if (!requireRole(session, ['OWNER', 'ADMIN', 'EDITOR'])) {
    return NextResponse.json({ error: { message: 'Forbidden: Insufficient permissions to ingest knowledge' } }, { status: 403 });
  }

  // Quota enforcement
  const quota = enforceQuota(session.workspaceId, 'chunks', 1);
  if (!quota.allowed && quota.response) {
    return quota.response;
  }

  try {
    const { name, type, rawContent, url, agentId } = await req.json();
    const content = rawContent || `Crawled content from ${url}`;
    if (!name || !content) {
      return NextResponse.json({ error: { message: 'Name and content are required' } }, { status: 400 });
    }

    const workspaceId = session.workspaceId || 'ws_acme_corp';
    const serviceToken = await createServiceJwt(workspaceId, session.user.id, session.role);

    const pyRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/knowledge/ingest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`
      },
      body: JSON.stringify({
        title: name,
        content: content,
        workspace_id: workspaceId,
        metadata: {
          type: type || (url ? 'WEBSITE' : 'DOCUMENT'),
          agent_id: agentId,
          source_url: url
        }
      })
    });

    if (!pyRes.ok) {
      const errData = await pyRes.json().catch(() => ({ detail: 'Backend ingestion failed' }));
      return NextResponse.json({ error: { message: errData.detail || 'Ingestion failed' } }, { status: pyRes.status });
    }

    const doc = await pyRes.json();
    return NextResponse.json({ success: true, document: doc });
  } catch (err: any) {
    return NextResponse.json({ error: { message: err.message || 'Ingestion failed' } }, { status: 500 });
  }
}
