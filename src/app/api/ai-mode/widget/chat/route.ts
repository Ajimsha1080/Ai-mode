import { NextResponse } from 'next/server';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

export async function POST(req: Request) {
  const widgetId = req.headers.get('x-ai-mode-widget-id');
  if (!widgetId) {
    return NextResponse.json({ error: 'x-ai-mode-widget-id header is required' }, { status: 400 });
  }

  try {
    const body = await req.json();
    const res = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/widget/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-AI-Mode-Widget-Id': widgetId
      },
      body: JSON.stringify({
        message: body.message,
        conversation_id: body.conversation_id || body.conversationId,
        session_id: body.session_id,
        context: body.context
      })
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
