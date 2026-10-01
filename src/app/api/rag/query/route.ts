import { NextResponse } from 'next/server';
import { getAuthSession, createServiceJwt } from '@/lib/auth';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

export async function POST(req: Request) {
  const session = await getAuthSession(req);
  if (!session) return NextResponse.json({ error: { message: 'Unauthorized' } }, { status: 401 });

  try {
    const { question, top_k, min_score, agent_id } = await req.json();
    if (!question) {
      return NextResponse.json({ error: { message: 'Question parameter is required' } }, { status: 400 });
    }

    const workspaceId = session.workspaceId;
    const serviceToken = await createServiceJwt(workspaceId, session.user.id, session.role);

    // Forward directly to Python FastAPI 12-Stage RAG Engine of Record
    const pythonRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/rag/query`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`
      },
      body: JSON.stringify({
        question,
        workspace_id: workspaceId,
        top_k: top_k || 3,
        min_score: min_score || 0.20,
        agent_id: agent_id
      })
    });

    if (pythonRes.ok) {
      const pythonData = await pythonRes.json();
      return NextResponse.json(pythonData);
    }

    const errData = await pythonRes.json().catch(() => ({ detail: 'RAG query failed' }));
    return NextResponse.json({ error: { message: errData.detail || 'RAG Query Failed' } }, { status: pythonRes.status });
  } catch (err: any) {
    return NextResponse.json({ error: { message: err.message || 'RAG Query Failed' } }, { status: 500 });
  }
}
