import { db } from '../db';

export interface ToolCallRequest {
  tool_id: string;
  parameters: Record<string, any>;
  workspace_id: string;
  agent_id: string;
  conversation_id: string;
}

export interface ToolCallResult {
  tool_id: string;
  status: 'SUCCESS' | 'FAILED' | 'CONFIRMATION_REQUIRED' | 'APPROVAL_REQUIRED' | 'PERMISSION_DENIED';
  message: string;
  data?: any;
  interactive_payload?: {
    type: 'PRODUCTS' | 'ORDER_TRACKING' | 'CONFIRMATION' | 'QUICK_REPLIES' | 'CART_SUMMARY';
    data: any;
  };
  latency_ms: number;
}

export async function executeTool(request: ToolCallRequest): Promise<ToolCallResult> {
  const startTime = Date.now();
  const { tool_id, parameters, workspace_id, agent_id } = request;

  const permission = db.tool_permissions.find(
    p => p.agent_id === agent_id && p.tool_id === tool_id
  );

  if (permission && !permission.is_enabled) {
    return {
      tool_id,
      status: 'PERMISSION_DENIED',
      message: 'Tool ' + tool_id + ' is disabled by merchant configuration.',
      latency_ms: Date.now() - startTime
    };
  }

  try {
    switch (tool_id) {
      case 'product_search': {
        const query = (parameters.query || '').toLowerCase();
        const maxPrice = parameters.max_price || parameters.maxPrice;
        const minPrice = parameters.min_price || parameters.minPrice;
        
        let products = db.commerce_products.filter(p => p.workspace_id === workspace_id);
        if (query) {
          products = products.filter(p => 
            p.title.toLowerCase().includes(query) ||
            p.category.toLowerCase().includes(query) ||
            (p.tags || []).some(t => t.toLowerCase().includes(query))
          );
        }
        if (maxPrice !== undefined) {
          products = products.filter(p => p.price <= maxPrice);
        }
        if (minPrice !== undefined) {
          products = products.filter(p => p.price >= minPrice);
        }

        return {
          tool_id,
          status: 'SUCCESS',
          message: 'Found ' + products.length + ' matching products.',
          data: products,
          interactive_payload: products.length > 0 ? {
            type: 'PRODUCTS',
            data: products.slice(0, 6)
          } : undefined,
          latency_ms: Date.now() - startTime
        };
      }

      case 'product_details': {
        const product = db.commerce_products.find(p => p.workspace_id === workspace_id && p.id === parameters.product_id);
        if (!product) {
          return {
            tool_id,
            status: 'FAILED',
            message: 'Product ID not found.',
            latency_ms: Date.now() - startTime
          };
        }
        return {
          tool_id,
          status: 'SUCCESS',
          message: 'Retrieved details for ' + product.title,
          data: product,
          interactive_payload: { type: 'PRODUCTS', data: [product] },
          latency_ms: Date.now() - startTime
        };
      }

      case 'inventory_lookup': {
        const product = db.commerce_products.find(p => p.workspace_id === workspace_id && p.id === parameters.product_id);
        const inStock = Boolean(product && product.total_inventory > 0 && product.in_stock !== false);
        return {
          tool_id,
          status: 'SUCCESS',
          message: inStock
            ? 'In stock with ' + (product?.total_inventory || 0) + ' units available.'
            : 'Currently out of stock.',
          data: { in_stock: inStock, available_quantity: product?.total_inventory || 0 },
          latency_ms: Date.now() - startTime
        };
      }

      case 'order_lookup': {
        if (!parameters.order_number || !parameters.customer_email) {
          return {
            tool_id,
            status: 'FAILED',
            message: 'Both order number and verified customer email are required to look up order details.',
            latency_ms: Date.now() - startTime
          };
        }
        const order = db.commerce_orders.find(o => 
          o.workspace_id === workspace_id &&
          o.order_number.toLowerCase() === parameters.order_number.toLowerCase() &&
          o.customer_email.toLowerCase() === parameters.customer_email.toLowerCase()
        );
        if (!order) {
          return {
            tool_id,
            status: 'FAILED',
            message: 'Order ' + parameters.order_number + ' was not found or the provided email does not match.',
            latency_ms: Date.now() - startTime
          };
        }
        const sanitizedOrder = {
          order_number: order.order_number,
          status: order.status,
          total_amount: order.total_amount,
          currency: order.currency,
          carrier: order.carrier,
          tracking_number: order.tracking_number,
          shipping_destination: '*** Redacted ***',
          items: order.items.map(i => ({ title: i.title, quantity: i.quantity, price: i.price }))
        };
        return {
          tool_id,
          status: 'SUCCESS',
          message: 'Order ' + order.order_number + ' is ' + order.status,
          data: sanitizedOrder,
          interactive_payload: {
            type: 'ORDER_TRACKING',
            data: sanitizedOrder
          },
          latency_ms: Date.now() - startTime
        };
      }

      case 'order_tracking': {
        if (!parameters.order_number || !parameters.customer_email) {
          return {
            tool_id,
            status: 'FAILED',
            message: 'Both order number and verified customer email are required to track order status.',
            latency_ms: Date.now() - startTime
          };
        }
        const order = db.commerce_orders.find(o => 
          o.workspace_id === workspace_id &&
          o.order_number.toLowerCase() === parameters.order_number.toLowerCase() &&
          o.customer_email.toLowerCase() === parameters.customer_email.toLowerCase()
        );
        if (!order) {
          return {
            tool_id,
            status: 'FAILED',
            message: 'Tracking info not found for order ' + parameters.order_number + ' or email does not match.',
            latency_ms: Date.now() - startTime
          };
        }
        return {
          tool_id,
          status: 'SUCCESS',
          message: 'Order ' + order.order_number + ' is ' + order.status,
          data: order,
          latency_ms: Date.now() - startTime
        };
      }

      case 'coupon_validation': {
        const code = (parameters.coupon_code || parameters.code || '').toUpperCase();
        const discounts: Record<string, number> = {
          WELCOME10: 0.10,
          SAVE20: 0.20,
          FLAT15: 0.15,
          TECHNOVANEW: 0.10
        };
        const valid = code in discounts;
        const discountAmount = valid ? (parameters.cart_subtotal || parameters.order_total || 100) * discounts[code] : 0;
        return {
          tool_id,
          status: valid ? 'SUCCESS' : 'FAILED',
          message: valid ? `Coupon ${code} applied successfully.` : `Invalid coupon code ${code}.`,
          data: { valid, code, discount_amount: discountAmount },
          latency_ms: Date.now() - startTime
        };
      }

      case 'return_eligibility': {
        return {
          tool_id,
          status: 'SUCCESS',
          message: 'Order is eligible for return within the 30-day return window.',
          data: { eligible: true, order_number: parameters.order_number, return_window_days: 30 },
          latency_ms: Date.now() - startTime
        };
      }

      case 'human_handoff': {
        const conv = db.conversations.find(c => c.id === request.conversation_id);
        if (conv) {
          conv.status = 'ESCALATED';
          conv.escalation_reason = parameters.reason || 'Customer requested live support agent';
          conv.updated_at = new Date().toISOString();
          db.scheduleSave();
        }
        return {
          tool_id,
          status: 'SUCCESS',
          message: 'Conversation escalated to human customer support team.',
          data: { escalated: true, reason: parameters.reason },
          latency_ms: Date.now() - startTime
        };
      }

      default:
        return {
          tool_id,
          status: 'FAILED',
          message: 'Unknown tool ' + tool_id,
          latency_ms: Date.now() - startTime
        };
    }
  } catch (err: any) {
    return {
      tool_id,
      status: 'FAILED',
      message: err.message || 'Execution error encountered in tool.',
      latency_ms: Date.now() - startTime
    };
  }
}
