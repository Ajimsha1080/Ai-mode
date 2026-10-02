import { NextResponse } from 'next/server';
import { getAuthSession, createServiceJwt } from '@/lib/auth';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

export async function POST(req: Request) {
  const session = await getAuthSession(req);
  const workspaceId = session?.workspaceId || 'ws_acme_corp';
  const userId = session?.user?.id || 'usr_guest_shopper';
  const userRole = session?.role || 'VIEWER';

  try {
    const body = await req.json();
    const serviceToken = await createServiceJwt(workspaceId, userId, userRole);

    const res = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/compare`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${serviceToken}`
      },
      body: JSON.stringify({
        product_ids: body.product_ids || [],
        user_query: body.user_query
      })
    });

    if (!res.ok) {
      return NextResponse.json({ error: 'Compare failed' }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
