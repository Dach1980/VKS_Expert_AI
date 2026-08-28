// ============================================================
// VKS Expert AI
// main.js v4
// ============================================================
//
// Главная точка входа приложения.
//
// Ответственность main.js:
//
// 1. Подключение модулей
// 2. Инициализация приложения
// 3. Навигация
// 4. Тема интерфейса
// 5. Глобальные keyboard shortcuts
// 6. Обработчики UI
// 7. Knowledge Base UI
// 8. Progress Modal
// 9. Координация генерации отчёта
// 10. Debug API
//
// НЕ содержит:
//
// - данные приложения              → state.js
// - универсальные utility-функции  → utils.js
// - renderer нормативов            → norms.js
// - renderer документов            → documents.js
// - renderer проверок              → checks.js
// - renderer отчётов               → reports.js
// - renderer Dashboard             → dashboard.js
// - настройки                      → settings.js
//
// Порядок загрузки:
//
// state.js
// utils.js
// main.js
//
// ============================================================

// ============================================================
// MODULES
// ============================================================

import './dashboard.js';
import './norms.js';
import './documents.js';
import './checks.js';
import './reports.js';
import './settings.js';

console.log('[VKS Expert AI] Main page modules loaded');

// ============================================================
// NAVIGATION
// ============================================================
//
// main.js отвечает за навигацию приложения.
//
// ВАЖНО:
// HTML использует ID вида:
//
// dashboardSection
// normsSection
// docsSection
// checksSection
// reportsSection
// settingsSection
//
// ============================================================

function navigateTo(section) {
  if (!section) {
    return;
  }

  console.log('[VKS Expert AI] Переход в раздел:', section);

  // ----------------------------------------------------------
  // Active navigation item
  // ----------------------------------------------------------

  document.querySelectorAll('.nav-item').forEach((item) => {
    item.classList.toggle('active', item.dataset.section === section);
  });

  // ----------------------------------------------------------
  // Hide all sections
  // ----------------------------------------------------------

  document.querySelectorAll('.section').forEach((sectionElement) => {
    sectionElement.classList.remove('active');
  });

  // ----------------------------------------------------------
  // Show target section
  // ----------------------------------------------------------

  const sectionElement = document.getElementById(`${section}Section`);

  if (sectionElement) {
    sectionElement.classList.add('active');
  } else {
    console.warn('[VKS Expert AI] Секция не найдена:', `${section}Section`);
  }

  // ----------------------------------------------------------
  // Breadcrumb
  // ----------------------------------------------------------

  const titles = {
    dashboard: 'Dashboard',
    norms: 'Нормы',
    docs: 'Документация',
    checks: 'Проверки',
    reports: 'Отчёты',
    settings: 'Настройки',
  };

  const breadcrumb = document.getElementById('breadcrumbCurrent');

  if (breadcrumb) {
    breadcrumb.textContent = titles[section] || section;
  }

  // ----------------------------------------------------------
  // Save current section to state
  // ----------------------------------------------------------

  if (typeof window.appState !== 'undefined' && window.appState) {
    window.appState.currentSection = section;
  }

  // ----------------------------------------------------------
  // Render section
  // ----------------------------------------------------------

  switch (section) {
    case 'dashboard':
      if (typeof window.renderDashboardTable === 'function') {
        window.renderDashboardTable();
      }

      if (typeof window.updateDashboardMetrics === 'function') {
        window.updateDashboardMetrics();
      }

      break;

    case 'norms':
      if (typeof window.renderNorms === 'function') {
        window.renderNorms();
      }

      break;

    case 'docs':
      if (typeof window.renderDocs === 'function') {
        window.renderDocs();
      }

      break;

    case 'checks':
      if (typeof window.renderChecks === 'function') {
        window.renderChecks();
      }

      break;

    case 'reports':
      if (typeof window.renderReports === 'function') {
        window.renderReports();
      }

      break;

    case 'settings':
      if (typeof window.renderSettings === 'function') {
        window.renderSettings();
      }

      break;

    default:
      break;
  }
}

window.navigateTo = navigateTo;

// ============================================================
// THEME
// ============================================================

function toggleTheme() {
  const html = document.documentElement;

  const currentTheme = html.getAttribute('data-theme');

  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

  html.setAttribute('data-theme', newTheme);

  const themeSwitch = document.getElementById('themeSwitch');

  if (themeSwitch) {
    themeSwitch.classList.toggle('active', newTheme === 'dark');
  }

  try {
    localStorage.setItem('vks-theme', newTheme);
  } catch (error) {
    console.warn('[VKS Expert AI] Не удалось сохранить тему:', error);
  }
}

window.toggleTheme = toggleTheme;

// ============================================================
// INITIALIZE THEME
// ============================================================

function initializeTheme() {
  let savedTheme = 'light';

  try {
    savedTheme = localStorage.getItem('vks-theme') || 'light';
  } catch (error) {
    console.warn('[VKS Expert AI] Не удалось прочитать тему:', error);
  }

  if (savedTheme !== 'light' && savedTheme !== 'dark') {
    savedTheme = 'light';
  }

  document.documentElement.setAttribute('data-theme', savedTheme);

  const themeSwitch = document.getElementById('themeSwitch');

  if (themeSwitch) {
    themeSwitch.classList.toggle('active', savedTheme === 'dark');
  }
}

// ============================================================
// BADGES
// ============================================================
//
// Реализация updateBadges находится в utils.js.
//
// Здесь только вызываем её.
//
// ============================================================

function refreshBadges() {
  if (typeof window.updateBadges === 'function') {
    window.updateBadges();
  }

  if (typeof window.updateKnowledgeBaseCounters === 'function') {
    window.updateKnowledgeBaseCounters();
  }
}

// ============================================================
// KNOWLEDGE BASE — OLD CHAT
// ============================================================
//
// Старый интерфейс чата.
//
// Используется для совместимости с существующей
// версией интерфейса.
//
// ============================================================

let chatHistory = [];

// ------------------------------------------------------------
// Example question
// ------------------------------------------------------------

function fillExampleQuestion(element) {
  if (!element) {
    return;
  }

  const input = document.getElementById('chatInput');

  if (!input) {
    return;
  }

  input.value = element.textContent.trim();

  sendChatMessage();
}

window.fillExampleQuestion = fillExampleQuestion;

// ------------------------------------------------------------
// Send chat message
// ------------------------------------------------------------

async function sendChatMessage() {
  const input = document.getElementById('chatInput');

  if (!input) {
    return;
  }

  const message = input.value.trim();

  if (!message) {
    return;
  }

  const searchInDocs =
    document.getElementById('searchInDocs')?.checked ?? false;

  input.value = '';

  addMessageToChat('user', message);

  showTypingIndicator();

  try {
    const response = await fetch(
      'http://127.0.0.1:8000/api/knowledge-base/query',
      {
        method: 'POST',

        headers: {
          'Content-Type': 'application/json',
        },

        body: JSON.stringify({
          question: message,
          search_in_docs: searchInDocs,
        }),
      },
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    hideTypingIndicator();

    if (data?.error) {
      addMessageToChat('assistant', `Ошибка: ${data.error}`);

      return;
    }

    addMessageToChat(
      'assistant',
      data?.answer || 'Сервер не вернул ответ.',
      data?.sources || null,
    );
  } catch (error) {
    hideTypingIndicator();

    console.error('[VKS Expert AI] Chat error:', error);

    addMessageToChat(
      'assistant',
      'Ошибка подключения к серверу. Убедитесь, что backend запущен на http://127.0.0.1:8000.',
    );
  }
}

window.sendChatMessage = sendChatMessage;

// ------------------------------------------------------------
// Add message
// ------------------------------------------------------------

function addMessageToChat(role, content, sources = null) {
  const messagesContainer = document.getElementById('chatMessages');

  if (!messagesContainer) {
    return;
  }

  const welcome = messagesContainer.querySelector('.chat-welcome');

  if (welcome) {
    welcome.remove();
  }

  const messageDiv = document.createElement('div');

  messageDiv.className = `chat-message ${role}`;

  const avatar = document.createElement('div');

  avatar.className = 'message-avatar';

  avatar.textContent = role === 'user' ? 'Вы' : 'AI';

  const contentDiv = document.createElement('div');

  contentDiv.className = 'message-content';

  const bubble = document.createElement('div');

  bubble.className = 'message-bubble';

  bubble.textContent = content || '';

  contentDiv.appendChild(bubble);

  // ----------------------------------------------------------
  // Sources
  // ----------------------------------------------------------

  if (Array.isArray(sources) && sources.length > 0) {
    const sourcesDiv = document.createElement('div');

    sourcesDiv.className = 'message-sources';

    const sourcesTitle = document.createElement('div');

    sourcesTitle.className = 'sources-title';

    sourcesTitle.textContent = 'Источники';

    sourcesDiv.appendChild(sourcesTitle);

    sources.forEach((source) => {
      const sourceItem = document.createElement('div');

      sourceItem.className = 'source-item';

      const icon = document.createElement('div');

      icon.className = 'source-icon';

      icon.innerHTML = `
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
          ></path>

          <polyline points="14 2 14 8 20 8"></polyline>
        </svg>
      `;

      const textDiv = document.createElement('div');

      textDiv.className = 'source-text';

      textDiv.textContent = source?.text || '';

      const meta = document.createElement('div');

      meta.className = 'source-meta';

      meta.textContent = `${source?.document || 'Документ'} • Стр. ${source?.page ?? '—'}`;

      textDiv.appendChild(meta);

      sourceItem.appendChild(icon);

      sourceItem.appendChild(textDiv);

      sourcesDiv.appendChild(sourceItem);
    });

    contentDiv.appendChild(sourcesDiv);
  }

  // ----------------------------------------------------------
  // Time
  // ----------------------------------------------------------

  const time = document.createElement('div');

  time.className = 'message-time';

  time.textContent = new Date().toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  });

  messageDiv.appendChild(avatar);

  messageDiv.appendChild(contentDiv);

  messageDiv.appendChild(time);

  messagesContainer.appendChild(messageDiv);

  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  chatHistory.push({
    role,
    content,
    sources,
    timestamp: new Date(),
  });
}

window.addMessageToChat = addMessageToChat;

// ------------------------------------------------------------
// Old chat typing indicator
// ------------------------------------------------------------

function showTypingIndicator() {
  const messagesContainer = document.getElementById('chatMessages');

  if (!messagesContainer) {
    return;
  }

  document.getElementById('typingIndicator')?.remove();

  const typingDiv = document.createElement('div');

  typingDiv.className = 'chat-message assistant';

  typingDiv.id = 'typingIndicator';

  const avatar = document.createElement('div');

  avatar.className = 'message-avatar';

  avatar.textContent = 'AI';

  const contentDiv = document.createElement('div');

  contentDiv.className = 'message-content';

  const bubble = document.createElement('div');

  bubble.className = 'message-bubble';

  bubble.innerHTML = `
    <div class="typing-indicator">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;

  contentDiv.appendChild(bubble);

  typingDiv.appendChild(avatar);

  typingDiv.appendChild(contentDiv);

  messagesContainer.appendChild(typingDiv);

  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  const sendButton = document.getElementById('chatSendBtn');

  if (sendButton) {
    sendButton.disabled = true;
  }
}

window.showTypingIndicator = showTypingIndicator;

function hideTypingIndicator() {
  document.getElementById('typingIndicator')?.remove();

  const sendButton = document.getElementById('chatSendBtn');

  if (sendButton) {
    sendButton.disabled = false;
  }
}

window.hideTypingIndicator = hideTypingIndicator;

// ============================================================
// KNOWLEDGE BASE COUNTERS
// ============================================================
//
// Здесь нет собственных данных.
//
// normsData / docsData берутся из state.js.
//
// ============================================================

function updateKnowledgeBaseCounters() {
  const normsCount = Array.isArray(window.normsData)
    ? window.normsData.length
    : 0;

  const docsCount = Array.isArray(window.docsData) ? window.docsData.length : 0;

  const normsBadge = document.getElementById('normsCount');

  const docsBadge = document.getElementById('docsCount');

  if (normsBadge) {
    const word =
      typeof window.getWordForm === 'function'
        ? window.getWordForm(normsCount, 'норма', 'нормы', 'норм')
        : 'норм';

    normsBadge.textContent = `${normsCount} ${word} загружено`;
  }

  if (docsBadge) {
    const word =
      typeof window.getWordForm === 'function'
        ? window.getWordForm(docsCount, 'документ', 'документа', 'документов')
        : 'документов';

    docsBadge.textContent = `${docsCount} ${word} загружено`;
  }
}

window.updateKnowledgeBaseCounters = updateKnowledgeBaseCounters;

// ============================================================
// KNOWLEDGE BASE — THREE PANEL
// ============================================================

let kbChatHistory = [];

let kbIsProcessing = false;

// ------------------------------------------------------------
// Left sidebar
// ------------------------------------------------------------

function toggleKBLeftSidebar() {
  const sidebar = document.getElementById('kbLeftSidebar');

  if (sidebar) {
    sidebar.classList.toggle('collapsed');
  }
}

window.toggleKBLeftSidebar = toggleKBLeftSidebar;

// ------------------------------------------------------------
// Right panel
// ------------------------------------------------------------

function toggleKBRightPanel() {
  const panel = document.getElementById('kbRightPanel');

  if (panel) {
    panel.classList.toggle('collapsed');
  }
}

window.toggleKBRightPanel = toggleKBRightPanel;

// ------------------------------------------------------------
// New KB chat
// ------------------------------------------------------------

function newKBChat() {
  kbChatHistory = [];

  const messagesContainer = document.getElementById('kbChatMessages');

  if (!messagesContainer) {
    return;
  }

  messagesContainer.innerHTML = `
    <div
      class="kb-welcome-screen"
      id="kbWelcomeScreen"
    >
      <div class="kb-welcome-icon">
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
          ></path>
        </svg>
      </div>

      <h2>База знаний</h2>

      <p>
        Задайте вопрос по нормативным документам
        или проектной документации.
        Система найдёт релевантную информацию
        и предоставит ответ с ссылками
        на источники.
      </p>

      <div class="kb-example-queries">

        <div
          class="kb-example-query"
          onclick="sendKBExample('Какие требования к диаметру труб для внутреннего водопровода согласно СП 30.13330.2020?')"
        >
          Какие требования к диаметру труб
          для внутреннего водопровода согласно
          СП 30.13330.2020?
        </div>

        <div
          class="kb-example-query"
          onclick="sendKBExample('Что говорит СП 30.13330.2020 о скорости воды в трубах и как её рассчитать?')"
        >
          Что говорит СП 30.13330.2020
          о скорости воды в трубах
          и как её рассчитать?
        </div>

        <div
          class="kb-example-query"
          onclick="sendKBExample('Как рассчитать потери напора в трубопроводе по формуле Дарси-Вейсбаха?')"
        >
          Как рассчитать потери напора
          в трубопроводе по формуле
          Дарси-Вейсбаха?
        </div>

      </div>
    </div>
  `;
}

window.newKBChat = newKBChat;

// ------------------------------------------------------------
// Example query
// ------------------------------------------------------------

function sendKBExample(question) {
  const input = document.getElementById('kbChatInput');

  if (!input) {
    return;
  }

  input.value = question;

  sendKBMessage();
}

window.sendKBExample = sendKBExample;

// ------------------------------------------------------------
// Keyboard input
// ------------------------------------------------------------

function handleKBInputKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();

    sendKBMessage();
  }
}

window.handleKBInputKeydown = handleKBInputKeydown;

// ------------------------------------------------------------
// Auto resize textarea
// ------------------------------------------------------------

function autoResizeKBInput(textarea) {
  if (!textarea) {
    return;
  }

  textarea.style.height = 'auto';

  textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
}

window.autoResizeKBInput = autoResizeKBInput;

// ------------------------------------------------------------
// Send KB message
// ------------------------------------------------------------

async function sendKBMessage() {
  const input = document.getElementById('kbChatInput');

  if (!input || kbIsProcessing) {
    return;
  }

  const message = input.value.trim();

  if (!message) {
    return;
  }

  const searchInNorms =
    document.getElementById('kbSearchInNorms')?.checked ?? false;

  const searchInDocs =
    document.getElementById('kbSearchInDocs')?.checked ?? false;

  document.getElementById('kbWelcomeScreen')?.remove();

  addKBMessageToChat('user', message);

  input.value = '';

  input.style.height = 'auto';

  kbIsProcessing = true;

  showKBTypingIndicator();

  try {
    const response = await fetch(
      'http://127.0.0.1:8000/api/knowledge-base/query',
      {
        method: 'POST',

        headers: {
          'Content-Type': 'application/json',
        },

        body: JSON.stringify({
          question: message,

          search_in_norms: searchInNorms,

          search_in_docs: searchInDocs,
        }),
      },
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    if (data?.error) {
      addKBMessageToChat('ai', `Ошибка: ${data.error}`);

      return;
    }

    addKBMessageToChat(
      'ai',
      data?.answer || 'Сервер не вернул текст ответа.',
      data?.sources || null,
    );
  } catch (error) {
    console.error('[VKS Expert AI] Ошибка отправки запроса:', error);

    addKBMessageToChat(
      'ai',
      'Извините, произошла ошибка при обработке запроса. Проверьте, что backend запущен на http://127.0.0.1:8000.',
    );
  } finally {
    hideKBTypingIndicator();

    kbIsProcessing = false;
  }
}

window.sendKBMessage = sendKBMessage;

// ------------------------------------------------------------
// Add KB message
// ------------------------------------------------------------

function addKBMessageToChat(role, content, sources = null) {
  const messagesContainer = document.getElementById('kbChatMessages');

  if (!messagesContainer) {
    return;
  }

  const messageDiv = document.createElement('div');

  messageDiv.className = `kb-message ${role}`;

  const avatar = document.createElement('div');

  avatar.className = 'kb-message-avatar';

  avatar.textContent = role === 'user' ? 'Вы' : 'AI';

  const contentDiv = document.createElement('div');

  contentDiv.className = 'kb-message-content';

  const textNode = document.createElement('div');

  textNode.textContent = content || '';

  contentDiv.appendChild(textNode);

  // ----------------------------------------------------------
  // Sources
  // ----------------------------------------------------------

  if (Array.isArray(sources) && sources.length > 0) {
    const sourcesDiv = document.createElement('div');

    sourcesDiv.className = 'kb-sources';

    const sourcesTitle = document.createElement('div');

    sourcesTitle.className = 'kb-sources-title';

    sourcesTitle.textContent = 'Источники';

    sourcesDiv.appendChild(sourcesTitle);

    sources.forEach((source) => {
      const sourceItem = document.createElement('div');

      sourceItem.className = 'kb-source-item';

      const sourceText = document.createElement('div');

      sourceText.className = 'kb-source-text';

      sourceText.textContent = source?.text || '';

      const sourceMeta = document.createElement('div');

      sourceMeta.className = 'kb-source-meta';

      sourceMeta.textContent = `${source?.document || 'Документ'} • Стр. ${source?.page ?? '—'}`;

      sourceItem.appendChild(sourceText);

      sourceItem.appendChild(sourceMeta);

      sourcesDiv.appendChild(sourceItem);
    });

    contentDiv.appendChild(sourcesDiv);
  }

  messageDiv.appendChild(avatar);

  messageDiv.appendChild(contentDiv);

  messagesContainer.appendChild(messageDiv);

  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  kbChatHistory.push({
    role,
    content,
    sources,
    timestamp: new Date(),
  });
}

window.addKBMessageToChat = addKBMessageToChat;

// ------------------------------------------------------------
// KB typing indicator
// ------------------------------------------------------------

function showKBTypingIndicator() {
  const messagesContainer = document.getElementById('kbChatMessages');

  if (!messagesContainer) {
    return;
  }

  document.getElementById('kbTypingIndicator')?.remove();

  const indicatorDiv = document.createElement('div');

  indicatorDiv.className = 'kb-message ai';

  indicatorDiv.id = 'kbTypingIndicator';

  const avatar = document.createElement('div');

  avatar.className = 'kb-message-avatar';

  avatar.textContent = 'AI';

  const contentDiv = document.createElement('div');

  contentDiv.className = 'kb-message-content';

  const typingIndicator = document.createElement('div');

  typingIndicator.className = 'kb-typing-indicator';

  typingIndicator.innerHTML = `
    <div class="kb-typing-dot"></div>
    <div class="kb-typing-dot"></div>
    <div class="kb-typing-dot"></div>
  `;

  contentDiv.appendChild(typingIndicator);

  indicatorDiv.appendChild(avatar);

  indicatorDiv.appendChild(contentDiv);

  messagesContainer.appendChild(indicatorDiv);

  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

window.showKBTypingIndicator = showKBTypingIndicator;

function hideKBTypingIndicator() {
  document.getElementById('kbTypingIndicator')?.remove();
}

window.hideKBTypingIndicator = hideKBTypingIndicator;

// ============================================================
// PROGRESS MODAL
// ============================================================

function showProgressModal() {
  document.getElementById('progressModalOverlay')?.classList.add('active');
}

window.showProgressModal = showProgressModal;

function hideProgressModal() {
  document.getElementById('progressModalOverlay')?.classList.remove('active');
}

window.hideProgressModal = hideProgressModal;

// ------------------------------------------------------------
// Progress
// ------------------------------------------------------------

function updateProgress(percent, timeLeft) {
  const numericPercent = Number(percent);

  const safePercent = Math.max(
    0,
    Math.min(100, Number.isFinite(numericPercent) ? numericPercent : 0),
  );

  const progressPercent = document.getElementById('progressPercent');

  const progressBarText = document.getElementById('progressBarText');

  const progressBarFill = document.getElementById('progressBarFill');

  const progressTime = document.getElementById('progressTime');

  if (progressPercent) {
    progressPercent.textContent = `${safePercent}%`;
  }

  if (progressBarText) {
    progressBarText.textContent = `${safePercent}%`;
  }

  if (progressBarFill) {
    progressBarFill.style.width = `${safePercent}%`;
  }

  if (progressTime) {
    progressTime.textContent =
      Number(timeLeft) > 0
        ? `Осталось: ~${Math.ceil(Number(timeLeft))} сек`
        : 'Завершено!';
  }
}

window.updateProgress = updateProgress;

// ------------------------------------------------------------
// Progress stages
// ------------------------------------------------------------

function updateStage(stageNumber) {
  const stages = document.querySelectorAll('.progress-stage');

  const safeStage = Number(stageNumber) || 1;

  stages.forEach((stage) => {
    const stageNum = Number.parseInt(stage.dataset.stage, 10);

    stage.classList.remove('active', 'completed');

    if (stageNum < safeStage) {
      stage.classList.add('completed');
    } else if (stageNum === safeStage) {
      stage.classList.add('active');
    }
  });
}

window.updateStage = updateStage;

// ============================================================
// REPORT GENERATION
// ============================================================
//
// Здесь находится только orchestration.
//
// Сам renderer отчётов находится в reports.js.
//
// ============================================================

let reportGenerationInterval = null;

// ------------------------------------------------------------
// Simulate report generation
// ------------------------------------------------------------

function simulateReportGeneration() {
  if (reportGenerationInterval) {
    clearInterval(reportGenerationInterval);

    reportGenerationInterval = null;
  }

  showProgressModal();

  updateProgress(0, 10);

  updateStage(1);

  const totalDuration = 10000;

  const interval = 100;

  const steps = totalDuration / interval;

  let currentStep = 0;

  reportGenerationInterval = setInterval(() => {
    currentStep++;

    const percent = Math.min(100, Math.floor((currentStep / steps) * 100));

    const timeLeft = Math.max(
      0,
      Math.ceil(((steps - currentStep) * interval) / 1000),
    );

    updateProgress(percent, timeLeft);

    if (percent < 25) {
      updateStage(1);
    } else if (percent < 50) {
      updateStage(2);
    } else if (percent < 75) {
      updateStage(3);
    } else {
      updateStage(4);
    }

    if (currentStep >= steps) {
      clearInterval(reportGenerationInterval);

      reportGenerationInterval = null;

      completeReportGeneration();
    }
  }, interval);
}

window.simulateReportGeneration = simulateReportGeneration;

// ------------------------------------------------------------
// Complete report generation
// ------------------------------------------------------------

function completeReportGeneration() {
  // ----------------------------------------------------------
  // Получаем актуальные данные из state.js
  // ----------------------------------------------------------

  const checks = Array.isArray(window.checksData) ? window.checksData : [];

  const violations = checks.filter(
    (check) => check.type === 'violation',
  ).length;

  const compliant = checks.filter((check) => check.type === 'compliant').length;

  const unchecked = checks.filter((check) => check.type === 'unchecked').length;

  const critical = checks.filter(
    (check) => check.severity === 'critical',
  ).length;

  const major = checks.filter((check) => check.severity === 'major').length;

  const minor = checks.filter((check) => check.severity === 'minor').length;

  const now = new Date();

  const report = {
    id:
      typeof window.nextReportId === 'number'
        ? window.nextReportId++
        : Date.now(),

    title: `Отчёт по проверкам от ${now.toLocaleDateString(
      'ru-RU',
    )} ${now.toLocaleTimeString('ru-RU')}`,

    date: now.toLocaleDateString('ru-RU'),

    totalChecks: checks.length,

    violations,

    compliant,

    unchecked,

    critical,

    major,

    minor,

    checks: checks.map((check) => ({
      ...check,
    })),
  };

  // ----------------------------------------------------------
  // Add report to state
  // ----------------------------------------------------------
  //
  // Если state.js предоставляет функцию addReport(),
  // используем её.
  //
  // Для совместимости с текущей архитектурой также
  // поддерживается window.reportsData.
  //
  // ----------------------------------------------------------

  if (typeof window.addReport === 'function') {
    window.addReport(report);
  } else if (Array.isArray(window.reportsData)) {
    window.reportsData.push(report);
  } else {
    console.warn('[VKS Expert AI] reportsData недоступен');

    return;
  }

  // ----------------------------------------------------------
  // Render reports
  // ----------------------------------------------------------

  if (typeof window.renderReports === 'function') {
    window.renderReports();
  }

  refreshBadges();

  // ----------------------------------------------------------
  // Finish
  // ----------------------------------------------------------

  setTimeout(() => {
    hideProgressModal();

    if (typeof window.showToast === 'function') {
      window.showToast('Отчёт успешно создан', 'success');
    }
  }, 500);
}

window.completeReportGeneration = completeReportGeneration;

// ============================================================
// FILTER HANDLERS
// ============================================================

function initializeFilters() {
  document.querySelectorAll('.filter-tab').forEach((tab) => {
    tab.addEventListener('click', function () {
      document.querySelectorAll('.filter-tab').forEach((item) => {
        item.classList.remove('active');
      });

      this.classList.add('active');

      // ----------------------------------------------------
      // Передаём фильтр в state.js,
      // если state API его предоставляет.
      // ----------------------------------------------------

      const filter = this.dataset.filter || 'all';

      if (typeof window.setCurrentFilter === 'function') {
        window.setCurrentFilter(filter);
      } else if (typeof window.appState !== 'undefined' && window.appState) {
        window.appState.currentFilter = filter;
      }

      // ----------------------------------------------------
      // Render checks
      // ----------------------------------------------------

      if (typeof window.renderChecks === 'function') {
        window.renderChecks();
      }
    });
  });
}

// ============================================================
// NAVIGATION HANDLERS
// ============================================================

function initializeNavigation() {
  document.querySelectorAll('.nav-item').forEach((item) => {
    item.addEventListener('click', function () {
      navigateTo(this.dataset.section);
    });
  });
}

// ============================================================
// DROPZONES
// ============================================================

function initializeDropzones() {
  const dropzones = [
    {
      id: 'normsDropzone',
      type: 'norms',
    },

    {
      id: 'docsDropzone',
      type: 'docs',
    },
  ];

  dropzones.forEach(({ id, type }) => {
    const dropzone = document.getElementById(id);

    if (!dropzone) {
      return;
    }

    dropzone.addEventListener('dragover', (event) => {
      event.preventDefault();

      if (typeof window.handleDragOver === 'function') {
        window.handleDragOver(event);
      }
    });

    dropzone.addEventListener('dragleave', (event) => {
      if (typeof window.handleDragLeave === 'function') {
        window.handleDragLeave(event);
      }
    });

    dropzone.addEventListener('drop', (event) => {
      event.preventDefault();

      if (typeof window.handleDrop === 'function') {
        window.handleDrop(event, type);
      }
    });
  });
}

// ============================================================
// CHAT EVENTS
// ============================================================

function initializeChat() {
  // ----------------------------------------------------------
  // Old chat
  // ----------------------------------------------------------

  const chatInput = document.getElementById('chatInput');

  if (chatInput) {
    chatInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();

        sendChatMessage();
      }
    });
  }

  // ----------------------------------------------------------
  // Knowledge Base chat
  // ----------------------------------------------------------

  const kbChatInput = document.getElementById('kbChatInput');

  if (kbChatInput) {
    kbChatInput.addEventListener('input', () => {
      autoResizeKBInput(kbChatInput);
    });

    kbChatInput.addEventListener('keydown', handleKBInputKeydown);
  }
}

// ============================================================
// KEYBOARD SHORTCUTS
// ============================================================

function initializeKeyboardShortcuts() {
  document.addEventListener('keydown', (event) => {
    // --------------------------------------------------------
    // Escape
    // --------------------------------------------------------

    if (event.key === 'Escape') {
      closeShortcuts();

      const progressModal = document.getElementById('progressModalOverlay');

      if (progressModal?.classList.contains('active')) {
        hideProgressModal();
      }

      return;
    }

    // --------------------------------------------------------
    // Ctrl only
    // --------------------------------------------------------

    if (!event.ctrlKey) {
      return;
    }

    switch (event.key.toLowerCase()) {
      case '1':
        event.preventDefault();

        navigateTo('dashboard');

        break;

      case '2':
        event.preventDefault();

        navigateTo('norms');

        break;

      case '3':
        event.preventDefault();

        navigateTo('docs');

        break;

      case '4':
        event.preventDefault();

        navigateTo('checks');

        break;

      case '5':
        event.preventDefault();

        navigateTo('reports');

        break;

      case '6':
        event.preventDefault();

        navigateTo('settings');

        break;

      case 'k':
        event.preventDefault();

        document.querySelector('.search-input')?.focus();

        break;

      case 'd':
        event.preventDefault();

        toggleTheme();

        break;

      case '?':
        event.preventDefault();

        document.getElementById('shortcutsOverlay')?.classList.add('active');

        break;

      default:
        break;
    }
  });
}

// ============================================================
// SHORTCUTS MODAL
// ============================================================

function closeShortcuts() {
  document.getElementById('shortcutsOverlay')?.classList.remove('active');
}

window.closeShortcuts = closeShortcuts;

// ============================================================
// THEME EVENT
// ============================================================

function initializeThemeToggle() {
  const themeToggle = document.getElementById('themeToggle');

  if (!themeToggle) {
    return;
  }

  themeToggle.addEventListener('click', toggleTheme);
}

// ============================================================
// MODULE RENDERING
// ============================================================

function initializeRenderers() {
  // ----------------------------------------------------------
  // Norms
  // ----------------------------------------------------------

  if (typeof window.renderNorms === 'function') {
    window.renderNorms();
  }

  // ----------------------------------------------------------
  // Documents
  // ----------------------------------------------------------

  if (typeof window.renderDocs === 'function') {
    window.renderDocs();
  }

  // ----------------------------------------------------------
  // Checks
  // ----------------------------------------------------------

  if (typeof window.renderChecks === 'function') {
    window.renderChecks();
  }

  // ----------------------------------------------------------
  // Reports
  // ----------------------------------------------------------

  if (typeof window.renderReports === 'function') {
    window.renderReports();
  }

  // ----------------------------------------------------------
  // Dashboard
  // ----------------------------------------------------------

  if (typeof window.renderDashboardTable === 'function') {
    window.renderDashboardTable();
  }

  if (typeof window.updateDashboardMetrics === 'function') {
    window.updateDashboardMetrics();
  }
}

// ============================================================
// SETTINGS INITIALIZATION
// ============================================================

function initializeSettings() {
  if (typeof window.loadStoragePaths === 'function') {
    window.loadStoragePaths();
  }

  if (typeof window.initializeSettings === 'function') {
    window.initializeSettings();
  }
}

// ============================================================
// APPLICATION INITIALIZATION
// ============================================================

function initializeApplication() {
  console.log('[VKS Expert AI] DOM ready');

  // ----------------------------------------------------------
  // Core
  // ----------------------------------------------------------

  initializeTheme();

  initializeNavigation();

  initializeDropzones();

  initializeFilters();

  initializeChat();

  initializeKeyboardShortcuts();

  initializeThemeToggle();

  initializeSettings();

  // ----------------------------------------------------------
  // Render modules
  // ----------------------------------------------------------

  initializeRenderers();

  // ----------------------------------------------------------
  // Badges
  // ----------------------------------------------------------

  refreshBadges();

  // ----------------------------------------------------------
  // Default section
  // ----------------------------------------------------------

  navigateTo('dashboard');

  console.log('[VKS Expert AI] Application initialized');
}

// ============================================================
// DOM READY
// ============================================================

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApplication, {
    once: true,
  });
} else {
  initializeApplication();
}

// ============================================================
// DEBUG API
// ============================================================
//
// ВАЖНО:
//
// Здесь не храним собственные копии массивов.
//
// Getter возвращает актуальное состояние.
//
// Это позволяет работать с:
//
// window.VKSExpertAI.normsData
// window.VKSExpertAI.docsData
// window.VKSExpertAI.checksData
// window.VKSExpertAI.reportsData
//
// ============================================================

window.VKSExpertAI = {
  // ----------------------------------------------------------
  // State getters
  // ----------------------------------------------------------

  get normsData() {
    return window.normsData;
  },

  get docsData() {
    return window.docsData;
  },

  get checksData() {
    return window.checksData;
  },

  get reportsData() {
    return window.reportsData;
  },

  get currentFilter() {
    if (typeof window.appState !== 'undefined' && window.appState) {
      return window.appState.currentFilter;
    }

    return undefined;
  },

  get currentSectionFilter() {
    if (typeof window.appState !== 'undefined' && window.appState) {
      return window.appState.currentSectionFilter;
    }

    return undefined;
  },

  get currentSeverityFilter() {
    if (typeof window.appState !== 'undefined' && window.appState) {
      return window.appState.currentSeverityFilter;
    }

    return undefined;
  },

  // ----------------------------------------------------------
  // Chat state
  // ----------------------------------------------------------

  get kbIsProcessing() {
    return kbIsProcessing;
  },

  get kbChatHistory() {
    return kbChatHistory;
  },

  get chatHistory() {
    return chatHistory;
  },

  // ----------------------------------------------------------
  // Navigation
  // ----------------------------------------------------------

  navigateTo,

  // ----------------------------------------------------------
  // Theme
  // ----------------------------------------------------------

  toggleTheme,

  initializeTheme,

  // ----------------------------------------------------------
  // UI
  // ----------------------------------------------------------

  showProgressModal,

  hideProgressModal,

  updateProgress,

  updateStage,

  closeShortcuts,

  // ----------------------------------------------------------
  // Knowledge Base
  // ----------------------------------------------------------

  sendKBMessage,

  addKBMessageToChat,

  newKBChat,

  sendKBExample,

  toggleKBLeftSidebar,

  toggleKBRightPanel,

  showKBTypingIndicator,

  hideKBTypingIndicator,

  // ----------------------------------------------------------
  // Old Chat
  // ----------------------------------------------------------

  sendChatMessage,

  addMessageToChat,

  showTypingIndicator,

  hideTypingIndicator,

  // ----------------------------------------------------------
  // Reports
  // ----------------------------------------------------------

  simulateReportGeneration,

  completeReportGeneration,

  // ----------------------------------------------------------
  // Counters
  // ----------------------------------------------------------

  updateKnowledgeBaseCounters,

  refreshBadges,

  // ----------------------------------------------------------
  // Initialization
  // ----------------------------------------------------------

  initializeApplication,
};

// ============================================================
// DEBUG
// ============================================================

console.log('[VKS Expert AI] main.js v4 loaded');
