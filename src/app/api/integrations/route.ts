import { NextResponse } from 'next/server';
import { getAuthSession, createServiceJwt } from '@/lib/auth';

export const dynamic = 'force-dynamic';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

export async function GET(req: Request) {
  const session = await getAuthSession(req);
  if (!session) return NextResponse.json({ error: { message: 'Unauthorized' } }, { status: 401 });

  try {
    const serviceToken = await createServiceJwt(session.workspaceId, session.user.id, session.role);
    const pyRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/connectors/`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${serviceToken}`,
        'X-Tenant-ID': session.workspaceId
      },
      signal: AbortSignal.timeout(10000)
    });

    const data = await pyRes.json();
    return NextResponse.json(data, { status: pyRes.status });
  } catch (err: any) {
    return NextResponse.json({ error: { message: 'Connector service error' } }, { status: 500 });
  }
}
