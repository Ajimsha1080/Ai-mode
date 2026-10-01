import { NextResponse } from 'next/server';
import { AUTH_COOKIE_NAME } from '@/lib/auth';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { email, password, name, workspace_name } = body;

    if (!email || !password || !name) {
      return NextResponse.json({ error: { message: 'Email, password, and name are required' } }, { status: 400 });
    }

    const pyRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name, workspace_name }),
      signal: AbortSignal.timeout(10000)
    });

    const data = await pyRes.json();
    if (!pyRes.ok) {
      return NextResponse.json(
        { error: { message: data.detail || data.error?.message || 'Failed to create account' } },
        { status: pyRes.status }
      );
    }

    const response = NextResponse.json({
      success: true,
      token: data.token,
      user: data.user,
      workspace_id: data.workspace_id
    });

    if (data.token) {
      response.cookies.set(AUTH_COOKIE_NAME, data.token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: 7 * 24 * 3600,
        path: '/'
      });
    }

    return response;
  } catch (err: any) {
    return NextResponse.json({ error: { message: 'Authentication service error' } }, { status: 500 });
  }
}
