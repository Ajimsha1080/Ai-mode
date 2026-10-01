import { NextResponse } from 'next/server';
import { getAuthSession, createServiceJwt, requireRole } from '@/lib/auth';

export const dynamic = 'force-dynamic';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

export async function POST(
  req: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { id: integrationId } = await context.params;
  const session = await getAuthSession(req);
  if (!session) return NextResponse.json({ error: { message: 'Unauthorized' } }, { status: 401 });

  if (!requireRole(session, ['OWNER', 'ADMIN', 'EDITOR'])) {
    return NextResponse.json({ error: { message: 'Forbidden: Insufficient permissions. Requires EDITOR, ADMIN, or OWNER role.' } }, { status: 403 });
  }

  let body: Record<string, any> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }

  try {
    const serviceToken = await createServiceJwt(session.workspaceId, session.user.id, session.role);
    const pyRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/connectors/${integrationId}/logs/replay`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`,
        'X-Tenant-ID': session.workspaceId
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10000)
    });

    const data = await pyRes.json();
    return NextResponse.json(data, { status: pyRes.status });
  } catch (err: any) {
    return NextResponse.json({ error: { message: 'Failed to replay event' } }, { status: 500 });
  }
}
