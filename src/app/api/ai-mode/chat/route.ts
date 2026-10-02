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

    const res = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${serviceToken}`
      },
      body: JSON.stringify({
        message: body.message,
        conversation_id: body.conversation_id || body.conversationId,
        session_id: body.session_id,
        channel: body.channel || 'PREVIEW',
        context: body.context
      })
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
