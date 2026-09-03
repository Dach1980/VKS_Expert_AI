// Project Expert AI — Knowledge Base / RAG test console
const API_URL = 'http://127.0.0.1:8000/api/knowledge-base/query';
let chatHistory = [];
let isProcessing = false;

function toggleLeftSidebar() {
  const sidebar = document.getElementById('leftSidebar');
  if (sidebar) sidebar.classList.toggle('collapsed');
}

function toggleRightPanel() {
  const panel = document.getElementById('rightPanel');
  if (panel) panel.classList.toggle('collapsed');
}

function goToHome() {
  if (window.history.length > 1) window.history.back();
  else alert('Откройте index.html для возврата на главную страницу');
}

function newChat() {
  chatHistory = [];
  const chatMessages = document.getElementById('chatMessages');
  if (!chatMessages) return;
  chatMessages.innerHTML = `
    <div class="welcome-screen" id="welcomeScreen">
      <div class="welcome-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg></div>
      <h2>База знаний</h2>
      <p>Задайте вопрос по нормативным документам или проектной документации. Система найдёт релевантную информацию и предоставит ответ с диагностикой RAG.</p>
      <div class="example-queries">
        <div class="example-query" onclick="sendExample('Какие требования к диаметру труб для внутреннего водопровода согласно СП 30.13330.2020?')">Какие требования к диаметру труб для внутреннего водопровода согласно СП 30.13330.2020?</div>
        <div class="example-query" onclick="sendExample('Что говорит СП 30.13330.2020 о скорости воды в трубах и как её рассчитать?')">Что говорит СП 30.13330.2020 о скорости воды в трубах и как её рассчитать?</div>
        <div class="example-query" onclick="sendExample('Как рассчитать потери напора в трубопроводе по формуле Дарси-Вейсбаха?')">Как рассчитать потери напора в трубопроводе по формуле Дарси-Вейсбаха?</div>
      </div>
    </div>`;
}

function sendExample(question) {
  const input = document.getElementById('chatInput');
  if (input) input.value = question;
  sendMessage();
}

function handleInputKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

function autoResizeInput(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
}

function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\"/g, '&quot;').replace(/'/g, '&#039;');
}

function formatContent(content) {
  if (content == null) return '';
  if (typeof content === 'string') return escapeHtml(content);
  if (typeof content === 'object') {
    return escapeHtml(content.text || content.formula || JSON.stringify(content));
  }
  return escapeHtml(content);
}

function formatSourceDocument(source) {
  const document = source?.document || 'unknown';
  const version = source?.version_label || source?.normative_version || '';
  return version && version !== document ? version : document;
}

function addDiagnosticsToChat(diagnostics, notice) {
  if (!diagnostics) return;
  const retrieved = Array.isArray(diagnostics.retrieved) ? diagnostics.retrieved : [];
  const accepted = Array.isArray(diagnostics.accepted) ? diagnostics.accepted : [];
  const rejected = Array.isArray(diagnostics.rejected) ? diagnostics.rejected : [];
  const d = diagnostics.diagnostics || {};
  const intent = diagnostics.intent || {};

  const rows = retrieved.map((item, index) => `
    <div class="rag-debug-item">
      <div><strong>#${index + 1}</strong> · ${escapeHtml(formatSourceDocument(item))} · стр. ${escapeHtml(item.page || 0)} · score ${Number(item.score || 0).toFixed(3)}</div>
      <div class="rag-debug-type">${escapeHtml(item.type || 'text')} · ${escapeHtml(item.source || 'faiss')}</div>
      <div class="rag-debug-text">${formatContent(item.content)}</div>
    </div>`).join('');

  const rejectedRows = rejected.map((item, index) => {
    const reason = item.reason || item.reasons || item.message || 'без указанной причины';
    const source = item.item || {};
    return `<div class="rag-debug-item"><strong>Отклонено #${index + 1}</strong> · ${escapeHtml(formatSourceDocument(source))} · стр. ${escapeHtml(source.page || 0)}<div class="rag-debug-text">Причина: ${escapeHtml(typeof reason === 'object' ? JSON.stringify(reason) : reason)}</div></div>`;
  }).join('');

  const block = document.createElement('details');
  block.className = 'rag-debug-panel';
  block.open = true;
  block.innerHTML = `
    <summary>Диагностика RAG · найдено ${d.retrieved_count || 0} · принято ${d.accepted_count || 0} · отклонено ${d.rejected_count || 0} · confidence ${Number(diagnostics.evidence_confidence || 0).toFixed(3)}</summary>
    <div class="rag-debug-body">
      ${notice ? `<div class="rag-debug-notice">${escapeHtml(notice)}</div>` : ''}
      <div class="rag-debug-meta"><b>Intent:</b> ${escapeHtml(JSON.stringify(intent))}</div>
      <div class="rag-debug-meta"><b>Enhanced query:</b><pre>${escapeHtml(diagnostics.enhanced_query || '')}</pre></div>
      <div class="rag-debug-meta"><b>Проверенный контекст:</b><pre>${escapeHtml(diagnostics.context || '[пусто]')}</pre></div>
      <div class="rag-debug-section"><b>Сырые результаты Retriever (${retrieved.length})</b>${rows || '<div class="rag-debug-empty">Retriever не вернул результатов.</div>'}</div>
      <div class="rag-debug-section"><b>Принятые evidence (${accepted.length})</b>${accepted.map(item => `<div class="rag-debug-item">${escapeHtml(formatSourceDocument(item))} · стр. ${escapeHtml(item.page || 0)} · score ${Number(item.score || 0).toFixed(3)}<div class="rag-debug-text">${formatContent(item.content)}</div></div>`).join('') || '<div class="rag-debug-empty">Нет принятых evidence.</div>'}</div>
      <div class="rag-debug-section"><b>Отклонённые evidence (${rejected.length})</b>${rejectedRows || '<div class="rag-debug-empty">Нет отклонённых evidence.</div>'}</div>
    </div>`;

  const aiMessages = document.querySelectorAll('#chatMessages .message.ai');
  const target = aiMessages[aiMessages.length - 1];
  if (target) target.querySelector('.message-content')?.appendChild(block);
}

function addMessageToChat(role, content, sources = null) {
  const welcomeScreen = document.getElementById('welcomeScreen');
  if (welcomeScreen) welcomeScreen.remove();
  const chatMessages = document.getElementById('chatMessages');
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;
  const avatar = role === 'user' ? 'Вы' : 'AI';
  let sourcesHTML = '';
  if (sources && sources.length > 0) {
    sourcesHTML = `<div class="sources-block"><div class="sources-title">Источники</div>${sources.map(source => `<div class="source-item"><span class="source-doc">${escapeHtml(formatSourceDocument(source))}</span><div>Страница: ${escapeHtml(source.page)}<br>Релевантность: ${Number(source.score || 0).toFixed(3)}</div></div>`).join('')}</div>`;
  }
  messageDiv.innerHTML = `<div class="message-avatar">${avatar}</div><div class="message-content">${content || ''}${sourcesHTML}</div>`;
  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTypingIndicator() {
  const chatMessages = document.getElementById('chatMessages');
  const typingDiv = document.createElement('div');
  typingDiv.className = 'message ai';
  typingDiv.id = 'typingIndicator';
  typingDiv.innerHTML = `<div class="message-avatar">AI</div><div class="message-content"><div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div></div>`;
  chatMessages.appendChild(typingDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
  const typingIndicator = document.getElementById('typingIndicator');
  if (typingIndicator) typingIndicator.remove();
}

async function sendMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  if (!message || isProcessing) return;

  const searchInNorms = document.getElementById('searchInNorms')?.checked ?? true;
  const searchInDocs = document.getElementById('searchInDocs')?.checked ?? false;
  addMessageToChat('user', escapeHtml(message));
  input.value = '';
  input.style.height = 'auto';
  showTypingIndicator();
  isProcessing = true;

  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        question: message,
        search_in_norms: searchInNorms,
        search_in_docs: searchInDocs,
        top_k: 5,
        diagnostics: true,
      }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    hideTypingIndicator();
    addMessageToChat('ai', data.answer, data.sources);
    addDiagnosticsToChat(data.diagnostics, data.diagnostic_notice);
  } catch (error) {
    hideTypingIndicator();
    addMessageToChat('ai', `Ошибка VKS Expert AI API: ${escapeHtml(error.message)}`);
  } finally {
    isProcessing = false;
  }
}

document.addEventListener('DOMContentLoaded', function () {
  console.log('Project Expert AI Knowledge Base / RAG diagnostics initialized');
  console.log('VKS API:', API_URL);
});
