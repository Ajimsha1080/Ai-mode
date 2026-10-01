import { NextResponse } from 'next/server';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

export async function GET(req: Request) {
  try {
    const url = new URL(req.url);
    const token = url.searchParams.get('token');
    const pyRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/auth/verify-email?token=${encodeURIComponent(token || '')}`, {
      method: 'GET',
      signal: AbortSignal.timeout(10000)
    });

    const data = await pyRes.json();
    return NextResponse.json(data, { status: pyRes.status });
  } catch (err: any) {
    return NextResponse.json({ error: { message: 'Authentication service error' } }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const pyRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/auth/verify-email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10000)
    });

    const data = await pyRes.json();
    return NextResponse.json(data, { status: pyRes.status });
  } catch (err: any) {
    return NextResponse.json({ error: { message: 'Authentication service error' } }, { status: 500 });
  }
}
