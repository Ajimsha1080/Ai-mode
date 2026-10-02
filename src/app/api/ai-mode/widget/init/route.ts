import { NextResponse } from 'next/server';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const widgetId = searchParams.get('widget_id');
  if (!widgetId) {
    return NextResponse.json({ error: 'widget_id query parameter is required' }, { status: 400 });
  }

  const origin = req.headers.get('origin') || '';

  try {
    const res = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/widget/init/${widgetId}`, {
      headers: {
        Origin: origin
      }
    });

    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ error: err }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
