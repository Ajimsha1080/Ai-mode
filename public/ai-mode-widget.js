/**
 * AI Mode Autonomous Website Shopping Widget
 * Decoupled, standalone, zero-dependency client script.
 */
(function () {
  var currentScript = document.currentScript || (function() {
    var scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();

  if (!currentScript) return;

  var widgetId = currentScript.getAttribute('data-ai-mode-widget-id') || 'aim_pub_demo';
  var apiUrl = currentScript.getAttribute('data-api-url') || window.location.origin;
  var position = currentScript.getAttribute('data-position') || 'bottom_right';
  var primaryColor = currentScript.getAttribute('data-primary-color') || '#6366f1';
  var launcherText = currentScript.getAttribute('data-launcher-text') || 'Ask AI Mode';

  if (document.getElementById('ai-mode-widget-root')) return;

  var root = document.createElement('div');
  root.id = 'ai-mode-widget-root';
  root.style.position = 'fixed';
  root.style.bottom = '24px';
  if (position === 'bottom_left') {
    root.style.left = '24px';
  } else {
    root.style.right = '24px';
  }
  root.style.zIndex = '999999';
  root.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';

  // Inject Styles
  var style = document.createElement('style');
  style.innerHTML = `
    #ai-mode-widget-root * { box-sizing: border-box; }
    .aim-launcher-btn {
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      color: #ffffff;
      background: ${primaryColor};
      border: none;
      padding: 12px 20px;
      border-radius: 9999px;
      font-size: 13px;
      font-weight: 700;
      box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.4), 0 8px 10px -6px rgba(0,0,0,0.1);
      transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s;
    }
    .aim-launcher-btn:hover { transform: scale(1.05); }
    .aim-launcher-btn:active { transform: scale(0.96); }

    .aim-window {
      position: absolute;
      bottom: 60px;
      ${position === 'bottom_left' ? 'left: 0;' : 'right: 0;'}
      width: 390px;
      max-width: calc(100vw - 32px);
      height: 600px;
      max-height: calc(100vh - 100px);
      background: #ffffff;
      color: #0f172a;
      border: 1px solid #e2e8f0;
      border-radius: 24px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      animation: aimFadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes aimFadeIn { from { opacity: 0; transform: translateY(12px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }

    .aim-header {
      padding: 16px;
      background: #0f172a;
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .aim-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      background: #f8fafc;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .aim-msg {
      max-width: 85%;
      padding: 12px 14px;
      font-size: 13px;
      line-height: 1.45;
      border-radius: 16px;
    }
    .aim-msg-assistant {
      background: #ffffff;
      color: #1e293b;
      border: 1px solid #e2e8f0;
      align-self: flex-start;
      box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .aim-msg-user {
      background: #0f172a;
      color: #ffffff;
      align-self: flex-end;
      border-bottom-right-radius: 4px;
    }
    .aim-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 10px;
      margin-top: 6px;
      display: flex;
      gap: 10px;
      align-items: center;
    }
    .aim-card img {
      width: 50px;
      height: 50px;
      object-fit: cover;
      border-radius: 8px;
    }
    .aim-card-title { font-weight: 700; font-size: 12px; color: #0f172a; }
    .aim-card-price { font-weight: 800; font-size: 13px; color: #4f46e5; margin-top: 2px; }
    .aim-card-btn {
      margin-left: auto;
      padding: 6px 10px;
      background: #0f172a;
      color: #fff;
      border: none;
      border-radius: 8px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
    }
    .aim-chip {
      background: #eef2ff;
      color: #4f46e5;
      border: 1px solid #c7d2fe;
      padding: 5px 10px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      display: inline-block;
      margin: 2px;
      transition: background 0.15s;
    }
    .aim-chip:hover { background: #e0e7ff; }
    .aim-footer {
      padding: 12px;
      background: #ffffff;
      border-top: 1px solid #e2e8f0;
      display: flex;
      gap: 8px;
    }
    .aim-input {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid #cbd5e1;
      border-radius: 12px;
      font-size: 13px;
      outline: none;
    }
    .aim-input:focus { border-color: #6366f1; }
    .aim-send-btn {
      padding: 10px 16px;
      background: ${primaryColor};
      color: #ffffff;
      border: none;
      border-radius: 12px;
      font-weight: 700;
      font-size: 12px;
      cursor: pointer;
    }
  `;
  document.head.appendChild(style);

  var isOpen = false;
  var conversationId = null;

  // Launcher Button
  var launcher = document.createElement('button');
  launcher.className = 'aim-launcher-btn';
  launcher.innerHTML = `<span>✨</span> <span>${launcherText}</span>`;

  // Window
  var chatWindow = document.createElement('div');
  chatWindow.className = 'aim-window';
  chatWindow.style.display = 'none';

  chatWindow.innerHTML = `
    <div class="aim-header">
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="font-size:16px;">✨</span>
        <div>
          <div style="font-weight:bold;font-size:13px;" id="aim-brand-title">AI Mode Concierge</div>
          <div style="font-size:10px;color:#94a3b8;">Autonomous Product Discovery</div>
        </div>
      </div>
      <button id="aim-close-btn" style="background:none;border:none;color:#94a3b8;font-size:18px;cursor:pointer;">✕</button>
    </div>
    <div class="aim-body" id="aim-messages-container">
      <div class="aim-msg aim-msg-assistant">
        Hello! 👋 I'm your AI Mode shopping assistant. What can I find for you in the catalog today?
        <div style="margin-top:8px;">
          <span class="aim-chip" onclick="window.sendAIModePrompt('Show UPF 50+ Sunscreen Jackets')">UPF 50+ Jackets</span>
          <span class="aim-chip" onclick="window.sendAIModePrompt('Items under ₹1,000')">Under ₹1,000</span>
          <span class="aim-chip" onclick="window.sendAIModePrompt('What is your return policy?')">Return Policy</span>
        </div>
      </div>
    </div>
    <div class="aim-footer">
      <input type="text" class="aim-input" id="aim-chat-input" placeholder="Ask anything about products..." />
      <button class="aim-send-btn" id="aim-send-trigger">Send</button>
    </div>
  `;

  root.appendChild(chatWindow);
  root.appendChild(launcher);
  document.body.appendChild(root);

  // Toggle Window
  function toggleChat() {
    isOpen = !isOpen;
    chatWindow.style.display = isOpen ? 'flex' : 'none';
    if (isOpen) {
      document.getElementById('aim-chat-input').focus();
    }
  }

  launcher.addEventListener('click', toggleChat);
  document.getElementById('aim-close-btn').addEventListener('click', toggleChat);

  // Send Message
  function sendMessage(text) {
    var inputEl = document.getElementById('aim-chat-input');
    var msgText = text || inputEl.value;
    if (!msgText.trim()) return;

    var container = document.getElementById('aim-messages-container');

    // Append User Message
    var userDiv = document.createElement('div');
    userDiv.className = 'aim-msg aim-msg-user';
    userDiv.innerText = msgText;
    container.appendChild(userDiv);
    if (!text) inputEl.value = '';
    container.scrollTop = container.scrollHeight;

    // Loading indicator
    var loadingDiv = document.createElement('div');
    loadingDiv.className = 'aim-msg aim-msg-assistant';
    loadingDiv.innerText = 'Searching catalog and formulating plan...';
    container.appendChild(loadingDiv);
    container.scrollTop = container.scrollHeight;

    fetch(apiUrl + '/api/ai-mode/widget/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-AI-Mode-Widget-Id': widgetId
      },
      body: JSON.stringify({
        message: msgText,
        conversation_id: conversationId,
        channel: 'WIDGET'
      })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        container.removeChild(loadingDiv);
        if (data.conversation_id) conversationId = data.conversation_id;

        var botDiv = document.createElement('div');
        botDiv.className = 'aim-msg aim-msg-assistant';
        botDiv.innerHTML = '<div>' + (data.response || 'Found relevant products.') + '</div>';

        // Render product cards if returned
        if (data.products && data.products.length > 0) {
          data.products.slice(0, 3).forEach(function (p) {
            var card = document.createElement('div');
            card.className = 'aim-card';
            var imgSrc = (p.images && p.images[0]) || 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=200';
            card.innerHTML = `
              <img src="${imgSrc}" alt="${p.title}" />
              <div style="flex:1;min-width:0;">
                <div class="aim-card-title" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${p.title}</div>
                <div class="aim-card-price">${p.currency} ${Number(p.price).toLocaleString()}</div>
              </div>
              <button class="aim-card-btn" onclick="alert('Added ${p.title} to cart!')">Add</button>
            `;
            botDiv.appendChild(card);
          });
        }

        // Suggestions
        if (data.suggestions && data.suggestions.length > 0) {
          var chipsDiv = document.createElement('div');
          chipsDiv.style.marginTop = '8px';
          data.suggestions.slice(0, 3).forEach(function (s) {
            var chip = document.createElement('span');
            chip.className = 'aim-chip';
            chip.innerText = s;
            chip.onclick = function () { sendMessage(s); };
            chipsDiv.appendChild(chip);
          });
          botDiv.appendChild(chipsDiv);
        }

        container.appendChild(botDiv);
        container.scrollTop = container.scrollHeight;
      })
      .catch(function (err) {
        container.removeChild(loadingDiv);
        var errDiv = document.createElement('div');
        errDiv.className = 'aim-msg aim-msg-assistant';
        errDiv.innerText = 'Sorry, could not process request right now.';
        container.appendChild(errDiv);
      });
  }

  window.sendAIModePrompt = function (text) {
    sendMessage(text);
  };

  document.getElementById('aim-send-trigger').addEventListener('click', function () {
    sendMessage();
  });

  document.getElementById('aim-chat-input').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      sendMessage();
    }
  });
})();
