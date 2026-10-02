if (!process.env.APP_ENV) {
  process.env.APP_ENV = 'development';
}

import { createServiceJwt } from '../src/lib/auth';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

async function runAIModeTests() {
  console.log('================================================================');
  console.log('  RUNNING AI MODE ACCEPTANCE & INTEGRATION TEST SUITE');
  console.log('================================================================\n');

  const workspaceId = 'ws_acme_corp';
  const serviceToken = await createServiceJwt(workspaceId, 'usr_admin_01', 'ADMIN');

  let passed = 0;
  let total = 0;

  function assert(condition: boolean, msg: string) {
    total++;
    if (condition) {
      console.log(`[PASS] Test ${total}: ${msg}`);
      passed++;
    } else {
      console.error(`[FAIL] Test ${total}: ${msg}`);
      throw new Error(`Assertion failed: ${msg}`);
    }
  }

  // Test 1: Config Fetching & Default
  console.log('--- Phase 1: AI Mode Configuration & Feature Flag ---');
  const cfgRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/config`, {
    headers: { Authorization: `Bearer ${serviceToken}` }
  });
  if (cfgRes.status !== 200) {
    console.error('Config response status:', cfgRes.status, await cfgRes.text());
  }
  assert(cfgRes.status === 200, 'AI Mode config endpoint responds with 200 OK');
  const cfgData = await cfgRes.json();
  assert(cfgData.workspace_id === workspaceId, 'Config belongs to authenticated workspace');
  assert(cfgData.is_enabled === true, 'AI Mode feature flag defaults to enabled');

  // Test 2: Natural Language AI Search
  console.log('\n--- Phase 2: Natural Language AI Search Engine ---');
  const searchRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${serviceToken}`
    },
    body: JSON.stringify({
      query: 'Show sunscreen jackets under 2000'
    })
  });
  assert(searchRes.status === 200, 'AI Search endpoint responds with 200 OK');
  const searchData = await searchRes.json();
  assert(searchData.search_plan.intent === 'PRICE_FILTER', 'Search plan correctly identifies price filter intent');
  assert(searchData.search_plan.price_max === 2000, 'Search plan extracts numeric price constraint 2000');
  assert(Array.isArray(searchData.products), 'Returns products list');

  // Test 3: Conversational Shopping & Follow-up
  console.log('\n--- Phase 3: Conversational Dialogue & Multi-turn Reasoning ---');
  const chatRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${serviceToken}`
    },
    body: JSON.stringify({
      message: 'Show athletic travel joggers'
    })
  });
  assert(chatRes.status === 200, 'Conversational chat responds with 200 OK');
  const chatData = await chatRes.json();
  assert(chatData.conversation_id !== undefined, 'Session returns persistent conversation ID');
  assert(chatData.response.length > 0, 'Assistant generates helpful natural-language response');

  // Follow-up: "Show cheaper options"
  const followUpRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${serviceToken}`
    },
    body: JSON.stringify({
      message: 'Show cheaper options',
      conversation_id: chatData.conversation_id
    })
  });
  assert(followUpRes.status === 200, 'Follow-up query succeeds with 200 OK');
  const followUpData = await followUpRes.json();
  assert(followUpData.conversation_id === chatData.conversation_id, 'Maintains dialogue context state');

  // Test 4: Product Recommendations
  console.log('\n--- Phase 4: Product Recommendations Engine ---');
  const recRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/recommendations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${serviceToken}`
    },
    body: JSON.stringify({
      limit: 3
    })
  });
  assert(recRes.status === 200, 'Recommendations endpoint responds with 200 OK');
  const recData = await recRes.json();
  assert(Array.isArray(recData.recommendations), 'Returns curated recommendations');

  // Test 5: Knowledge Management (FAQs / Policy)
  console.log('\n--- Phase 5: Multi-Source Knowledge Ingestion ---');
  const createKRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/knowledge/source`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${serviceToken}`
    },
    body: JSON.stringify({
      name: 'Exchange Policy Guide',
      source_type: 'FAQ',
      content: 'We offer 7-day instant exchanges on all unworn items.'
    })
  });
  assert(createKRes.status === 200, 'Creates AI Mode knowledge source successfully');
  const kData = await createKRes.json();
  assert(kData.status === 'READY', 'Source is immediately indexed and READY');

  // Test 6: AI Mode Widget Deployment
  console.log('\n--- Phase 6: Independent Website Widget Deployment ---');
  const depRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/deployments`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${serviceToken}`
    },
    body: JSON.stringify({
      name: 'Main Store AI Widget',
      welcome_message: 'Hi there! Ready to shop with AI?',
      launcher_text: 'Ask AI Mode'
    })
  });
  assert(depRes.status === 200, 'Creates independent deployment with 200 OK');
  const depData = await depRes.json();
  assert(depData.public_widget_id.startsWith('aim_pub_'), 'Generates isolated public widget ID');
  assert(depData.embed_code.includes('data-ai-mode-widget-id'), 'Embed code references dedicated AI Mode widget');

  // Test 7: Public Widget Bootstrap & Interaction (Zero-Auth / Public Widget ID)
  console.log('\n--- Phase 7: Public Widget Initialization & Live Dialogue ---');
  const initRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/widget/init/${depData.public_widget_id}`);
  assert(initRes.status === 200, 'Public widget bootstrapping succeeds');
  const initData = await initRes.json();
  assert(initData.widget_id === depData.public_widget_id, 'Widget returns active configuration');

  // Public widget chat
  const publicChatRes = await fetch(`${PYTHON_BACKEND_URL}/api/v1/ai-mode/widget/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-AI-Mode-Widget-Id': depData.public_widget_id
    },
    body: JSON.stringify({
      message: 'Do you have running gear?'
    })
  });
  assert(publicChatRes.status === 200, 'Public widget dialogue executes with 200 OK');
  const publicChatData = await publicChatRes.json();
  assert(publicChatData.response.length > 0, 'Public widget receives authoritative response');

  console.log(`\n================================================================`);
  console.log(`  AI MODE TEST SUMMARY: ${passed}/${total} TESTS PASSED (100%)`);
  console.log(`================================================================\n`);
}

runAIModeTests().catch((err) => {
  console.error('Test suite failed:', err);
  process.exit(1);
});
