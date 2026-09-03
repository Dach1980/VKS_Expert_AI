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
  const document = source?.document_number || source?.document || 'unknown';
  const version = source?.version_label || source?.normative_version || '';
  if (!version || version === document) return document;
  if (version.toLowerCase().includes(document.toLowerCase())) return version;
  return `${document} — ${version}`;
}

function installAnswerStyles() {
  if (document.getElementById('vksAnswerStyles')) return;
  const style = document.createElement('style');
  style.id = 'vksAnswerStyles';
  style.textContent = `
    .vks-answer { line-height: 1.65; }
    .vks-answer h3 { margin: 18px 0 9px; font-size: 16px; font-weight: 700; }
    .vks-answer h3:first-child { margin-top: 0; }
    .vks-answer p { margin: 7px 0; }
    .vks-answer ul { margin: 8px 0 10px 20px; }
    .vks-answer li { margin: 4px 0; }
    .vks-answer .answer-highlight { margin: 10px 0 14px; padding: 12px 14px; border-radius: 10px; background: var(--bg-secondary, rgba(127,127,127,.08)); font-weight: 600; }
    .vks-answer .answer-table-wrap { overflow-x: auto; margin: 10px 0 14px; }
    .vks-answer table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .vks-answer th, .vks-answer td { padding: 9px 10px; border: 1px solid var(--border-color, rgba(127,127,127,.22)); text-align: left; vertical-align: top; }
    .vks-answer th { font-weight: 700; background: var(--bg-secondary, rgba(127,127,127,.08)); }
    .vks-answer .answer-conclusion { margin-top: 16px; padding: 13px 15px; border-radius: 10px; border: 1px solid var(--border-color, rgba(127,127,127,.22)); }
    .vks-answer .answer-conclusion strong { display: block; margin-bottom: 5px; }
    .sources-block { margin-top: 18px; }
    .sources-table-wrap { overflow-x: auto; margin-top: 9px; }
    .sources-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .sources-table th, .sources-table td { padding: 8px 9px; border: 1px solid var(--border-color, rgba(127,127,127,.22)); text-align: left; }
    .sources-table th { font-weight: 700; background: var(--bg-secondary, rgba(127,127,127,.08)); }
  `;
  document.head.appendChild(style);
}

function renderAnswer(answer) {
  installAnswerStyles();
  let text = String(answer == null ? '' : answer).trim();
  if (!text) return '<div class="vks-answer"><p>Ответ не получен.</p></div>';

  // The current model output uses section labels without markdown headings.
  // Normalize them first so the UI remains readable even before the prompt is upgraded.
  text = text
    .replace(/\s*Краткий вывод\s*/i, '\n\n### Краткий вывод\n')
    .replace(/\s*Расчет\s*\/\s*требования\s*/i, '\n\n### Требования\n')
    .replace(/\s*Источник\s*СП\s*/i, '\n\n### Источник СП\n');

  const lines = text.split(/\r?\n/);
  let html = '<div class="vks-answer">';
  let paragraph = [];
  let inList = false;
  let tableRows = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const value = paragraph.join(' ').trim();
    if (value) html += `<p>${formatInline(value)}</p>`;
    paragraph = [];
  };
  const flushList = () => {
    if (!inList) return;
    html += '</ul>';
    inList = false;
  };
  const flushTable = () => {
    if (!tableRows.length) return;
    const rows = tableRows.filter(row => row.length && !/^\s*[-:|\s]+$/.test(row.join('')));
    if (rows.length) {
      const header = rows[0];
      const body = rows.slice(1);
      html += '<div class="answer-table-wrap"><table><thead><tr>' + header.map(cell => `<th>${formatInline(cell)}</th>`).join('') + '</tr></thead><tbody>';
      body.forEach(row => { html += '<tr>' + row.map(cell => `<td>${formatInline(cell)}</td>`).join('') + '</tr>'; });
      html += '</tbody></table></div>';
    }
    tableRows = [];
  };

  const formatInline = value => escapeHtml(value)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');

  lines.forEach(raw => {
    const line = raw.trim();
    if (!line) { flushParagraph(); flushList(); flushTable(); return; }
    if (/^\|.*\|$/.test(line)) {
      flushParagraph(); flushList();
      tableRows.push(line.replace(/^\||\|$/g, '').split('|').map(cell => cell.trim()));
      return;
    }
    if (/^###\s+/.test(line)) {
      flushParagraph(); flushList(); flushTable();
      const title = line.replace(/^###\s+/, '').trim();
      html += `<h3>${escapeHtml(title)}</h3>`;
      return;
    }
    if (/^[-*]\s+/.test(line)) {
      flushParagraph(); flushTable();
      if (!inList) { html += '<ul>'; inList = true; }
      html += `<li>${formatInline(line.replace(/^[-*]\s+/, ''))}</li>`;
      return;
    }
    flushList(); flushTable();
    paragraph.push(line);
  });
  flushParagraph(); flushList(); flushTable();
  html += '</div>';

  // Emphasize the short conclusion when the answer starts with it.
  const answerRoot = document.createElement('div');
  answerRoot.innerHTML = html;
  const firstParagraph = answerRoot.querySelector('.vks-answer p');
  if (firstParagraph) firstParagraph.classList.add('answer-highlight');
  return answerRoot.innerHTML;
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
    sourcesHTML = `<div class="sources-block"><div class="sources-title">Источники</div><div class="sources-table-wrap"><table class="sources-table"><thead><tr><th>Нормативный документ</th><th>Страница</th><th>Релевантность</th></tr></thead><tbody>${sources.map(source => `<tr><td class="source-doc">${escapeHtml(formatSourceDocument(source))}</td><td>${escapeHtml(source.page)}</td><td>${Number(source.score || 0).toFixed(3)}</td></tr>`).join('')}</tbody></table></div></div>`;
  }
  const body = role === 'ai' ? renderAnswer(content) : escapeHtml(content || '');
  messageDiv.innerHTML = `<div class="message-avatar">${avatar}</div><div class="message-content">${body}${sourcesHTML}</div>`;
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
  addMessageToChat('user', message);
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
