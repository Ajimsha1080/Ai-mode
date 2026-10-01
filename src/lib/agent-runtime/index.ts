import { execFileSync } from 'child_process';
import path from 'path';
import { db } from '../db';
import { createServiceJwt } from '../auth';
import { ExecutionTrace } from '@/types';

export interface AgentRunParams {
  agent_id: string;
  workspace_id: string;
  conversation_id?: string;
  user_message: string;
  channel?: 'WEBSITE' | 'MOBILE' | 'API' | 'PLAYGROUND' | 'CUSTOM';
  customer_identifier?: string;
}

export interface AgentRunResponse {
  conversation_id: string;
  message_id: string;
  response_text: string;
  interactive_payload?: any;
  metadata?: any;
  trace: ExecutionTrace;
}

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

function runAgentCyclePythonProcess(params: AgentRunParams): AgentRunResponse {
  const pythonBackendDir = path.resolve(process.cwd(), 'python-backend');
  const pyCode = `
import os, sys, json
os.environ["APP_ENV"] = "dev"
sys.path.insert(0, r"${pythonBackendDir.replace(/\\/g, '\\\\')}")
from app.agent_runtime import run_agent_cycle
payload = json.loads(sys.stdin.read())
res = run_agent_cycle(
    agent_id=payload.get("agent_id"),
    message=payload.get("user_message"),
    conversation_id=payload.get("conversation_id"),
    workspace_id=payload.get("workspace_id"),
    tenant_products=payload.get("tenant_products"),
    tenant_chunks=payload.get("tenant_chunks"),
    tenant_orders=payload.get("tenant_orders"),
    customer_identifier=payload.get("customer_identifier")
)
print(json.dumps(res))
`;

  try {
    const tenantProducts = db.commerce_products.filter(p => p.workspace_id === params.workspace_id);
    const tenantChunks = db.knowledge_chunks.filter(c => c.workspace_id === params.workspace_id);
    const tenantOrders = db.commerce_orders.filter(o => o.workspace_id === params.workspace_id);

    const inputJson = JSON.stringify({
      agent_id: params.agent_id,
      user_message: params.user_message,
      conversation_id: params.conversation_id,
      workspace_id: params.workspace_id,
      tenant_products: tenantProducts.length > 0 ? tenantProducts : undefined,
      tenant_chunks: tenantChunks.length > 0 ? tenantChunks : undefined,
      tenant_orders: tenantOrders.length > 0 ? tenantOrders : undefined,
      customer_identifier: params.customer_identifier
    });

    const output = execFileSync('python', ['-c', pyCode], {
      input: inputJson,
      encoding: 'utf-8',
      cwd: pythonBackendDir,
      timeout: 15000,
      env: { ...process.env, APP_ENV: 'dev' }
    });

    // Parse the last JSON line from stdout
    const lines = output.trim().split('\n');
    const lastLine = lines[lines.length - 1];
    const data = JSON.parse(lastLine);

    return {
      conversation_id: data.conversation_id || params.conversation_id || 'conv_default',
      message_id: data.message_id || 'msg_' + Math.random().toString(36).substring(2, 9),
      response_text: data.response || '',
      interactive_payload: data.interactive_payload || null,
      metadata: data.metadata || (data.interactive_payload ? { products: data.interactive_payload.data, pagination: data.interactive_payload.pagination } : undefined),
      trace: data.trace || { steps: [] }
    };
  } catch (err: any) {
    console.error('Python child process fallback error:', err);
    return {
      conversation_id: params.conversation_id || 'conv_default',
      message_id: 'msg_err',
      response_text: 'I apologize, but the AI shopping engine encountered an error. Please try again.',
      trace: { steps: [] } as any
    };
  }
}

export async function runAgentCycle(params: AgentRunParams): Promise<AgentRunResponse> {
  const { agent_id, workspace_id, conversation_id, user_message, channel } = params;

  // 1. Try Live HTTP FastAPI Proxy
  try {
    const serviceToken = await createServiceJwt(workspace_id, 'usr_bff_node', 'ADMIN');
    const res = await fetch(`${PYTHON_BACKEND_URL}/api/v1/agents/${agent_id}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`
      },
      body: JSON.stringify({
        message: user_message,
        conversation_id,
        workspace_id,
        channel: channel || 'PLAYGROUND'
      }),
      signal: AbortSignal.timeout(6000)
    });

    if (res.ok) {
      const data = await res.json();
      return {
        conversation_id: data.conversation_id || conversation_id,
        message_id: data.message_id || 'msg_' + Math.random().toString(36).substring(2, 9),
        response_text: data.response,
        interactive_payload: data.interactive_payload,
        metadata: data.metadata || (data.interactive_payload ? { products: data.interactive_payload.data, pagination: data.interactive_payload.pagination } : undefined),
        trace: data.trace
      };
    }
  } catch {}

  // 2. Direct In-Process Python Runtime Fallback
  return runAgentCyclePythonProcess(params);
}
