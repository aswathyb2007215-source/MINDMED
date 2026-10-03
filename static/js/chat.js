/**
 * MINDMED AI Companion Interactive Chat Script
 */

document.addEventListener('DOMContentLoaded', () => {
  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendBtn');
  const promptChips = document.querySelectorAll('.chip');

  if (!chatForm || !chatMessages || !chatInput) return;

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  scrollToBottom();

  function appendMessage(sender, text, isCrisis = false, timeStr = null) {
    const time = timeStr || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const row = document.createElement('div');
    row.className = `message-bubble-row msg-${sender}`;

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = sender === 'ai' ? 'MM' : 'You';

    const contentDiv = document.createElement('div');
    contentDiv.style.display = 'flex';
    contentDiv.style.flexDirection = 'column';

    const bubble = document.createElement('div');
    bubble.className = `msg-bubble ${isCrisis ? 'msg-crisis-alert' : ''}`;
    
    // Parse simple markdown bold / bullet points for clean rendering
    let formattedText = escapeHtml(text);
    formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formattedText = formattedText.replace(/\*(.*?)\*/g, '<em>$1</em>');
    bubble.innerHTML = formattedText;

    const timeDiv = document.createElement('div');
    timeDiv.className = 'msg-time';
    timeDiv.textContent = time;

    contentDiv.appendChild(bubble);
    contentDiv.appendChild(timeDiv);

    row.appendChild(avatar);
    row.appendChild(contentDiv);
    chatMessages.appendChild(row);
    scrollToBottom();
  }

  function escapeHtml(string) {
    const entityMap = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    };
    return String(string).replace(/[&<>"']/g, s => entityMap[s]);
  }

  function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'typingIndicator';
    indicator.className = 'message-bubble-row msg-ai';
    indicator.innerHTML = `
      <div class="msg-avatar">MM</div>
      <div class="msg-bubble" style="color: var(--slate-400); font-style: italic;">
        MindMED Companion is typing...
      </div>
    `;
    chatMessages.appendChild(indicator);
    scrollToBottom();
  }

  function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
  }

  async function sendMessage(text) {
    if (!text.trim()) return;

    // Append user message immediately
    appendMessage('user', text);
    chatInput.value = '';
    chatInput.disabled = true;
    sendBtn.disabled = true;

    showTypingIndicator();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ message: text })
      });

      removeTypingIndicator();

      if (response.ok) {
        const data = await response.json();
        appendMessage('ai', data.reply, data.is_crisis, data.timestamp);
      } else {
        appendMessage('ai', "I'm having trouble connecting right now. Please try again in a moment.");
      }
    } catch (err) {
      removeTypingIndicator();
      appendMessage('ai', "Network error. Please check your connection and try again.");
    } finally {
      chatInput.disabled = false;
      sendBtn.disabled = false;
      chatInput.focus();
    }
  }

  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    sendMessage(chatInput.value);
  });

  // Prompt Chips
  promptChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt) {
        sendMessage(prompt);
      }
    });
  });
});
