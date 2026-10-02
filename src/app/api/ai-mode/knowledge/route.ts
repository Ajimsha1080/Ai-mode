import { NextResponse } from 'next/server';
import { getAuthSession, createServiceJwt } from '@/lib/auth';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

export async function GET(req: Request) {
  const session = await getAuthSession(req);
  const workspaceId = session?.workspaceId || 'ws_acme_corp';
  const userId = session?.user?.id || 'usr_admin_01';
  const userRole = session?.role || 'ADMIN';

  try {
    const serviceToken = await createServiceJwt(workspaceId, userId, userRole);
    const res = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/knowledge`, {
      headers: { Authorization: `Bearer ${serviceToken}` }
    });
    if (!res.ok) {
      return NextResponse.json({ error: 'Failed to fetch knowledge' }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  const session = await getAuthSession(req);
  const workspaceId = session?.workspaceId || 'ws_acme_corp';
  const userId = session?.user?.id || 'usr_admin_01';
  const userRole = session?.role || 'ADMIN';

  try {
    const body = await req.json();
    const serviceToken = await createServiceJwt(workspaceId, userId, userRole);

    const res = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/knowledge/source`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${serviceToken}`
      },
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      const errText = await res.text();
      return NextResponse.json({ error: errText }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function DELETE(req: Request) {
  const { searchParams } = new URL(req.url);
  const sourceId = searchParams.get('source_id');
  if (!sourceId) {
    return NextResponse.json({ error: 'source_id required' }, { status: 400 });
  }

  const session = await getAuthSession(req);
  const workspaceId = session?.workspaceId || 'ws_acme_corp';
  const userId = session?.user?.id || 'usr_admin_01';
  const userRole = session?.role || 'ADMIN';

  try {
    const serviceToken = await createServiceJwt(workspaceId, userId, userRole);
    const res = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/knowledge/source/${sourceId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${serviceToken}` }
    });
    if (!res.ok) {
      return NextResponse.json({ error: 'Failed to delete' }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
