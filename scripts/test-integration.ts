import assert from 'assert';

process.env.APP_ENV = 'development';
process.env.SESSION_JWT_SECRET = 'super_secure_production_session_jwt_secret_987654321_aaas';
process.env.SERVICE_JWT_SECRET = 'super_secure_production_service_jwt_secret_123456789_aaas';
process.env.INTERNAL_SERVICE_SECRET = process.env.SERVICE_JWT_SECRET;

import { seedDatabaseIfEmpty } from '../src/lib/db/seed';
import { db, getDatabase } from '../src/lib/db';
import { hashPassword, verifyPassword, createSessionToken, verifySessionToken, createServiceJwt } from '../src/lib/auth';
import { executeTool } from '../src/lib/tools';
import { runAgentCycle } from '../src/lib/agent-runtime';
import { runAgentEvaluations } from '../src/lib/evaluations';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

async function runAllTests() {
  console.log('========================================================');
  console.log('🚀 RUNNING SHOPMATE AAAS PLATFORM VERIFICATION SUITE');
  console.log('========================================================\n');

  let passed = 0;
  let failed = 0;

  async function test(name: string, fn: () => Promise<void>) {
    try {
      process.stdout.write(`[TEST] ${name} ... `);
      await fn();
      console.log('✅ PASSED');
      passed++;
    } catch (err: any) {
      console.log('❌ FAILED');
      console.error('       ', err.message);
      failed++;
    }
  }

  // 1. Database & Seeder
  await test('1. Database Engine & Seed Integrity', async () => {
    await seedDatabaseIfEmpty(true);
    const database = getDatabase();
    
    assert(database.users.length >= 2, 'Must have at least 2 users');
    assert(database.workspaces.length >= 1, 'Must have at least 1 workspace');
    assert(database.agents.length >= 1, 'Must have at least 1 agent');
    assert(database.commerce_products.length >= 4, 'Must have at least 4 products');
    assert(database.commerce_orders.length >= 1, 'Must have at least 1 order');
  });

  // 2. Authentication & JWT Tokens
  await test('2. Authentication, Hashing & JWT RBAC', async () => {
    const plain = 'superSecurePass2026!';
    const hash = await hashPassword(plain);
    const valid = await verifyPassword(plain, hash);
    const invalid = await verifyPassword('wrongPass', hash);
    
    assert.strictEqual(valid, true, 'Password verification should succeed');
    assert.strictEqual(invalid, false, 'Invalid password should fail');

    const token = await createSessionToken({
      userId: 'usr_merchant_01',
      email: 'merchant@shopmate.com',
      workspaceId: 'ws_acme_corp',
      isSuperAdmin: false
    });

    const payload = await verifySessionToken(token);
    assert(payload, 'JWT payload must be decoded');
    assert.strictEqual(payload?.email, 'merchant@shopmate.com');
  });

  // 3. RAG Semantic Embedding & Vector Search
  await test('3. Advanced RAG Semantic Retrieval', async () => {
    const serviceToken = await createServiceJwt('ws_acme_corp', 'usr_admin', 'ADMIN');
    const res = await fetch(`${PYTHON_BACKEND_URL}/api/v1/rag/query`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`
      },
      body: JSON.stringify({ question: 'What is the return policy for unworn items?', workspace_id: 'ws_acme_corp' })
    });
    assert(res.ok, 'RAG query endpoint should respond with 200 OK');
    const data = await res.json();
    assert(data.answer || data.citations, 'Must return grounded RAG result');
  });

  // 4. Commerce Engine & Tool Dispatcher
  await test('4. Commerce Engine & Tool Execution Engine', async () => {
    // Product search with budget constraint
    const searchRes = await executeTool({
      tool_id: 'product_search',
      parameters: { query: 'jacket', max_price: 2000 },
      workspace_id: 'ws_acme_corp',
      agent_id: 'agent_shopmate_01',
      conversation_id: 'conv_test_1'
    });
    assert.strictEqual(searchRes.status, 'SUCCESS');
    assert(searchRes.data.length > 0, 'Must find Sunscreen Jackets under ₹2000');
    assert(searchRes.data.every((p: any) => p.price <= 2000), 'All products must satisfy maxPrice <= 2000');

    // Searching non-existent items must return empty
    const noShoesRes = await executeTool({
      tool_id: 'product_search',
      parameters: { query: 'shoes' },
      workspace_id: 'ws_acme_corp',
      agent_id: 'agent_shopmate_01',
      conversation_id: 'conv_test_1'
    });
    assert.strictEqual(noShoesRes.data.length, 0, 'Must not return jackets for shoes query');

    // Order lookup
    const orderRes = await executeTool({
      tool_id: 'order_lookup',
      parameters: { order_number: '#10482', customer_email: 'sarah.sharma@gmail.com' },
      workspace_id: 'ws_acme_corp',
      agent_id: 'agent_shopmate_01',
      conversation_id: 'conv_test_1'
    });
    assert.strictEqual(orderRes.status, 'SUCCESS');
    assert(orderRes.data.order_number, 'Order details must be returned');

    // 7-Day Return Eligibility
    const returnRes = await executeTool({
      tool_id: 'return_eligibility',
      parameters: { order_number: '#10482' },
      workspace_id: 'ws_acme_corp',
      agent_id: 'agent_shopmate_01',
      conversation_id: 'conv_test_1'
    });
    assert.strictEqual(returnRes.status, 'SUCCESS');

    // Coupon validation
    const couponRes = await executeTool({
      tool_id: 'coupon_validation',
      parameters: { coupon_code: 'WELCOME10', order_total: 100 },
      workspace_id: 'ws_acme_corp',
      agent_id: 'agent_shopmate_01',
      conversation_id: 'conv_test_1'
    });
    assert.strictEqual(couponRes.status, 'SUCCESS');
  });

  // 5. Multi-Step Autonomous Agent Runtime
  await test('5. Multi-Step Agent Runtime with Trace Logging', async () => {
    // A. Product query should return products
    const prodResult = await runAgentCycle({
      agent_id: 'agent_shopmate_01',
      workspace_id: 'ws_acme_corp',
      user_message: 'Show me Sunscreen Jackets',
      channel: 'PLAYGROUND'
    });
    assert(prodResult.response_text.length > 0, 'Agent must produce a text response');
    assert(prodResult.interactive_payload, 'Must attach interactive product payload cards');
    assert.strictEqual(prodResult.interactive_payload.type, 'PRODUCTS');

    // B. Non-existent item query must NOT attach product cards
    const shoesResult = await runAgentCycle({
      agent_id: 'agent_shopmate_01',
      workspace_id: 'ws_acme_corp',
      user_message: 'RUNNING SHOES',
      channel: 'PLAYGROUND'
    });
    assert(shoesResult.response_text.length > 0, 'Agent must respond about shoes');
    assert.strictEqual(shoesResult.interactive_payload, null, 'Must NOT attach product cards when 0 products matched');
  });

  // 6. Automated Evaluations Runner
  await test('6. Automated Evaluations Runner Suite', async () => {
    const evalRun = await runAgentEvaluations('ws_acme_corp', 'agent_shopmate_01');
    assert(evalRun.metrics, 'Metrics object must be calculated');
    assert(evalRun.results.length >= 1, 'Must execute test cases');
  });

  console.log('\n========================================================');
  console.log(`📊 TEST SUITE SUMMARY: ${passed} PASSED | ${failed} FAILED`);
  console.log('========================================================\n');

  if (failed > 0) {
    process.exit(1);
  }
}

runAllTests().catch((err) => {
  console.error('Test runner fatal crash:', err);
  process.exit(1);
});
