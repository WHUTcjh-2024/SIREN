/**
 * ai_assistant_loader.js — 智慧星 AI 助手交互
 */
(function () {
  'use strict';

  var mascotBtn = document.getElementById('ai-mascot-btn');
  var chatPanel = document.getElementById('ai-chat-panel');
  var chatBackdrop = document.getElementById('ai-chat-backdrop');
  var closeBtn = document.getElementById('ai-close-btn');
  var sendBtn = document.getElementById('ai-send-btn');
  var input = document.getElementById('ai-chat-input');
  var messages = document.getElementById('ai-chat-messages');
  var chatNavBtn = document.getElementById('chat-nav-btn');
  var chatNavBtnSidebar = document.getElementById('chat-nav-btn-sidebar');

  function openChat() {
    if (chatPanel) chatPanel.classList.add('is-open');
    if (chatBackdrop) chatBackdrop.classList.add('is-open');
  }
  function closeChat() {
    if (chatPanel) chatPanel.classList.remove('is-open');
    if (chatBackdrop) chatBackdrop.classList.remove('is-open');
  }

  if (mascotBtn) mascotBtn.addEventListener('click', openChat);
  if (closeBtn) closeBtn.addEventListener('click', closeChat);
  if (chatBackdrop) chatBackdrop.addEventListener('click', closeChat);
  if (chatNavBtn) chatNavBtn.addEventListener('click', openChat);
  if (chatNavBtnSidebar) chatNavBtnSidebar.addEventListener('click', function (e) {
    e.preventDefault();
    openChat();
  });

  function addMessage(text, type) {
    if (!messages) return;
    var div = document.createElement('div');
    div.className = 'ai-msg ai-msg--' + type;
    var avatar = type === 'bot' ? '🌟' : '你';
    div.innerHTML =
      '<div class="ai-msg-avatar">' + avatar + '</div>' +
      '<div class="ai-msg-bubble">' + text + '</div>';
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function handleSend() {
    if (!input || !input.value.trim()) return;
    var text = input.value.trim();
    addMessage(text, 'user');
    input.value = '';
    input.style.height = 'auto';

    // Simulate bot response
    setTimeout(function () {
      var responses = [
        '好的，让我想想这个问题～',
        '这是一个很好的问题！在物理实验中，理解原理很重要。',
        '你可以试试在实验指导中查看详细步骤。',
        '如果遇到困难，不要着急，慢慢来～',
        '记得在拍照前确保激光对准液面哦！'
      ];
      var idx = Math.floor(Math.random() * responses.length);
      addMessage(responses[idx], 'bot');
    }, 800);
  }

  if (sendBtn) sendBtn.addEventListener('click', handleSend);
  if (input) {
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    });
    input.addEventListener('input', function () {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 100) + 'px';
    });
  }

  // Welcome message
  document.addEventListener('DOMContentLoaded', function () {
    if (messages && messages.children.length === 0) {
      addMessage('你好！我是智慧星 🌟 你的实验小助手。有任何问题都可以问我哦～', 'bot');
    }
  });
})();
