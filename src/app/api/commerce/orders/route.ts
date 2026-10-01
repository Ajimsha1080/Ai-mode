import { NextResponse } from 'next/server';
import { getAuthSession, createServiceJwt } from '@/lib/auth';
import { db } from '@/lib/db';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';
const orderRateLimitMap = new Map<string, number[]>();

function checkOrderRateLimit(key: string, limit: number = 10, windowMs: number = 60000): boolean {
  const now = Date.now();
  const timestamps = (orderRateLimitMap.get(key) || []).filter(ts => now - ts < windowMs);
  if (timestamps.length >= limit) {
    return false;
  }
  timestamps.push(now);
  orderRateLimitMap.set(key, timestamps);
  return true;
}

export async function GET(req: Request) {
  const session = await getAuthSession(req);
  if (!session) return NextResponse.json({ error: { message: 'Unauthorized' } }, { status: 401 });

  const clientIp = req.headers.get('x-forwarded-for')?.split(',')[0].trim() || 'local_ip';
  const rateLimitKey = `${clientIp}:${session.workspaceId}`;
  if (!checkOrderRateLimit(rateLimitKey, 10, 60000)) {
    return NextResponse.json(
      { error: { message: 'Too many order lookup requests. Please retry in a few moments.' } },
      { status: 429 }
    );
  }

  const { searchParams } = new URL(req.url);
  const orderNumber = searchParams.get('order_number');
  const customerEmail = searchParams.get('customer_email');

  if (orderNumber) {
    if (!customerEmail) {
      return NextResponse.json(
        { error: { message: 'Both order_number and customer_email are required.' } },
        { status: 400 }
      );
    }

    const serviceToken = await createServiceJwt(session.workspaceId, session.user.id, session.role);
    try {
      const pyRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/orders/${encodeURIComponent(orderNumber)}?customer_email=${encodeURIComponent(customerEmail)}`, {
        headers: { 'Authorization': `Bearer ${serviceToken}` },
        signal: AbortSignal.timeout(5000)
      });
      if (pyRes.ok) {
        const order = await pyRes.json();
        return NextResponse.json({ order });
      }
    } catch {}

    // Database lookup fallback
    const order = db.commerce_orders.find(o => 
      o.workspace_id === session.workspaceId &&
      o.order_number.toLowerCase() === orderNumber.toLowerCase() &&
      o.customer_email.toLowerCase() === customerEmail.toLowerCase()
    );

    if (!order) {
      return NextResponse.json(
        { error: { message: 'Order not found with the provided email address.' } },
        { status: 404 }
      );
    }
    return NextResponse.json({ order });
  }

  const orders = db.commerce_orders.filter(o => o.workspace_id === session.workspaceId);
  return NextResponse.json({ orders });
}
