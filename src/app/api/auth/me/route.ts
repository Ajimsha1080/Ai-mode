import { NextResponse } from 'next/server';
import { getAuthSession, AUTH_COOKIE_NAME } from '@/lib/auth';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

export async function GET(req: Request) {
  try {
    const session = await getAuthSession(req);
    if (!session) {
      return NextResponse.json({ authenticated: false, user: null });
    }

    const authHeader = req.headers.get('authorization') || '';
    const cookieHeader = req.headers.get('cookie') || '';

    const pyRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/auth/me`, {
      headers: {
        'Authorization': authHeader.startsWith('Bearer ') ? authHeader : `Bearer ${session.token || ''}`,
        'Cookie': cookieHeader
      },
      signal: AbortSignal.timeout(5000)
    });

    if (pyRes.ok) {
      const data = await pyRes.json();
      return NextResponse.json({
        authenticated: true,
        user: data.user || session.user,
        workspace_id: data.workspace_id || session.workspaceId,
        role: session.role
      });
    }

    return NextResponse.json({
      authenticated: true,
      user: session.user,
      workspace: { id: session.workspaceId, name: 'Store Workspace' },
      role: session.role
    });
  } catch {
    const session = await getAuthSession(req);
    if (session) {
      return NextResponse.json({
        authenticated: true,
        user: session.user,
        workspace: { id: session.workspaceId, name: 'Store Workspace' },
        role: session.role
      });
    }
    return NextResponse.json({ authenticated: false, user: null });
  }
}
