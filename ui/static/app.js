document.addEventListener('DOMContentLoaded', () => {
  const chatForm = document.getElementById('chatForm');
  const userInput = document.getElementById('userInput');
  const sendBtn = document.getElementById('sendBtn');
  const messagesStream = document.getElementById('messagesStream');
  const clearChatBtn = document.getElementById('clearChatBtn');
  const welcomeHero = document.getElementById('welcomeHero');

  let isGenerating = false;

  // Auto-resize textarea
  userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 150) + 'px';
  });

  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isGenerating && userInput.value.trim()) {
        chatForm.requestSubmit();
      }
    }
  });

  clearChatBtn.addEventListener('click', () => {
    messagesStream.innerHTML = '';
    if (welcomeHero) messagesStream.appendChild(welcomeHero);
  });

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query || isGenerating) return;

    // Reset input
    userInput.value = '';
    userInput.style.height = 'auto';
    if (welcomeHero) welcomeHero.style.display = 'none';

    appendUserMessage(query);
    const typingId = appendTypingIndicator();
    isGenerating = true;
    sendBtn.disabled = true;

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      const data = await response.json();
      removeElement(typingId);
      
      if (!response.ok || data.error) {
        appendAssistantMessage('An error occurred. Please try again later.');
      } else if (!data.allowed) {
        appendAssistantMessage(data.message || 'I cannot answer this query.');
      } else {
        appendAssistantMessage(data.answer, data.source_url);
      }
    } catch (err) {
      removeElement(typingId);
      appendAssistantMessage('Failed to connect to the server.');
    } finally {
      isGenerating = false;
      sendBtn.disabled = false;
      userInput.focus();
    }
  });

  function appendUserMessage(text) {
    const row = document.createElement('div');
    row.className = 'message-row user';
    row.innerHTML = `
      <div class="message-avatar"></div>
      <div class="message-body">
        <div class="bubble">
          <p>${escapeHtml(text)}</p>
        </div>
      </div>
    `;
    messagesStream.appendChild(row);
    scrollToBottom();
  }

  function appendTypingIndicator() {
    const id = 'typing-' + Date.now();
    const row = document.createElement('div');
    row.className = 'message-row assistant';
    row.id = id;
    row.innerHTML = `
      <div class="message-avatar"><i class="fa-solid fa-chart-pie"></i></div>
      <div class="message-body">
        <div class="bubble">
          <p class="typing">Thinking...</p>
          <p style="font-size: 0.85em; opacity: 0.7; margin-top: 4px;">Please be patient while relevant information is being searched.</p>
        </div>
      </div>
    `;
    messagesStream.appendChild(row);
    scrollToBottom();
    return id;
  }

  const FOLLOW_UP_QUESTIONS = [
    "What is the expense ratio for SBI Blue Chip Fund?",
    "How can I pause or stop my SIP?",
    "What is the lock-in period for ELSS funds?",
    "How do I download my capital gains statement?",
    "What are the risks in Small Cap mutual funds?",
    "What is the minimum initial investment for SBI Flexicap?",
    "What is the exit load on SBI Small Cap Fund?",
    "What is Net Asset Value (NAV)?",
    "How is capital gains tax calculated?",
    "Can I switch between regular and direct plans?"
  ];

  function getFollowUpQuestions(count = 3) {
    const shuffled = [...FOLLOW_UP_QUESTIONS].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, count);
  }

  function appendAssistantMessage(text, sourceUrl = '') {
    const row = document.createElement('div');
    row.className = 'message-row assistant';
    let formattedText = escapeHtml(text).replace(/\n/g, '<br>');
    
    let sourceHtml = '';
    if (sourceUrl) {
      sourceHtml = `<a href="${escapeHtml(sourceUrl)}" target="_blank" class="citation-link">
        <i class="fa-solid fa-arrow-up-right-from-square"></i> Source Document
      </a>`;
    }

    const suggestions = getFollowUpQuestions(3);
    const followUpHtml = `
      <div class="follow-up-container">
        ${suggestions.map(q => `<button class="follow-up-pill" data-query="${escapeHtml(q)}">${escapeHtml(q)}</button>`).join('')}
      </div>
    `;

    row.innerHTML = `
      <div class="message-avatar"><i class="fa-solid fa-chart-pie"></i></div>
      <div class="message-body">
        <div class="bubble">
          <p>${formattedText}</p>
          ${sourceHtml}
          ${followUpHtml}
        </div>
      </div>
    `;
    messagesStream.appendChild(row);

    // Add click listeners to new follow-up pills
    row.querySelectorAll('.follow-up-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        const query = btn.getAttribute('data-query');
        if (query) {
          userInput.value = query;
          chatForm.requestSubmit();
        }
      });
    });

    scrollToBottom();
  }

  function removeElement(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function scrollToBottom() {
    messagesStream.scrollTop = messagesStream.scrollHeight;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;');
  }

  // Handle Initial Suggestion Cards Clicks
  const suggestionCards = document.querySelectorAll('.suggestion-card');
  suggestionCards.forEach(card => {
    card.addEventListener('click', () => {
      const query = card.getAttribute('data-query');
      if (query) {
        userInput.value = query;
        chatForm.requestSubmit();
      }
    });
  });
});
