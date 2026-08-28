import './dashboard.js';
import './norms.js';
import './documents.js';
import './checks.js';
import './reports.js';
import './settings.js';

console.log('[VKS Expert AI] Main page modules loaded');

// ===== DATA STORAGE =====
let normsData = [
  {
    id: 1,
    docId: 1,
    docName: 'Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1_подпись (2).pdf',
    title: 'СП 30.13330.2020',
    subtitle:
      'Внутренний водопровод и канализация зданий. СНиП 2.04.01-85 (с Изменениями N 1-5)',
    date: '2021-07-01',
    points: 342,
    status: 'indexed',
    progress: 100,
    sections: ['ВК'],
    fileName: 'СП 30.13330.2020.pdf',
  },
];

let docsData = [
  {
    id: 1,
    docId: 1,
    docName: 'Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1_подпись (2).pdf',
    name: 'Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1_подпись (2).pdf',
    size: '4.8 МБ',
    date: '2026-05-21',
    status: 'checked',
    sheets: 22,
    section: 'ВК',
    checked: false,
  },
];

let checksData = [
  {
    id: 1,
    docId: 1,
    docName: 'Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1_подпись (2).pdf',
    type: 'violation',
    severity: 'critical',
    title:
      'Использована устаревшая редакция СП 30.13330.2012 вместо действующей СП 30.13330.2020',
    sheet: 'Лист 3.1-04',
    norm: 'СП 30.13330.2020',
    description:
      'Документ ссылается на СП 30.13330.2012, которая была заменена на СП 30.13330.2020 (действует с 2021-07-01).',
    recommendation:
      'Заменить все ссылки на СП 30.13330.2012 на СП 30.13330.2020.',
  },
  {
    id: 2,
    docId: 1,
    docName: 'Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1_подпись (2).pdf',
    type: 'violation',
    severity: 'critical',
    title: 'Не указан расчётный расход сточных вод для канализационной системы',
    sheet: 'Лист 3.1-05',
    norm: 'СП 30.13330.2020, п. 5.5.1',
    description:
      'В документе указаны диаметры ∅110, ∅160, ∅250, но отсутствует гидравлический расчёт расходов сточных вод. Цитата из нормы: «5.5.1 Диаметры труб и уклоны трубопроводов следует устанавливать расчётом.»',
    recommendation:
      'Предоставить гидравлический расчёт для всех канализационных трубопроводов.',
  },
  {
    id: 3,
    docId: 1,
    docName: 'Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1_подпись (2).pdf',
    type: 'violation',
    severity: 'major',
    title: 'Уклон трубопровода D=110 мм i=0.01 ниже рекомендуемого',
    sheet: 'Лист 3.1-03',
    norm: 'СП 30.13330.2020, п. 8.3.2',
    description:
      'В документе указан уклон i=0.01 для D110. Цитата: «8.3.2 Уклоны трубопроводов следует принимать: для труб диаметром 40-50 мм — 0,03; для труб диаметром 80-100 мм — 0,02; для труб диаметром 150 мм — 0,008.» Для D=110 минимальный уклон должен быть не менее 0.02.',
    recommendation:
      'Увеличить уклон до i≥0.02 или предоставить обосновывающий расчёт.',
  },
  {
    id: 4,
    docId: 1,
    docName: 'Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1_подпись (2).pdf',
    type: 'violation',
    severity: 'major',
    title: 'Отсутствует обоснование выбора материала трубопроводов',
    sheet: 'Лист 3.1-04',
    norm: 'СП 30.13330.2020, п. 5.3.2',
    description:
      'В документе указаны ПЭ трубы (4926-005-41989945-97), но отсутствует обоснование выбора материала на основе условий эксплуатации. Цитата: «5.3.2 Трубопроводы следует предусматривать из труб, отвечающих требованиям прочности, герметичности и стойкости к коррозии и зарастанию, допущенных к применению в строительстве в установленном порядке.»',
    recommendation:
      'Добавить раздел обоснования материала со ссылкой на параметры эксплуатации (температура, давление, среда).',
  },
  {
    id: 5,
    docId: 1,
    docName: 'Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1_подпись (2).pdf',
    type: 'violation',
    severity: 'minor',
    title: 'Не указаны отметки прокладки трубопроводов на плане 1-го этажа',
    sheet: 'Лист 3.1-01',
    norm: 'СП 30.13330.2020, п. 5.5.12',
    description:
      'Цитата: «5.5.12 Трубопроводы следует прокладывать с учётом архитектурно-планировочных и технологических требований.»',
    recommendation:
      'Добавить отметки высот прокладки трубопроводов на планах этажей.',
  },
  {
    id: 6,
    docId: 1,
    docName: 'Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1_подпись (2).pdf',
    type: 'violation',
    severity: 'minor',
    title: 'Неполное указание нормативных документов в перечне',
    sheet: 'Лист 3.1-07',
    norm: 'СП 30.13330.2020',
    description:
      'Перечень нормативных ссылок (лист 12) не включает все применимые стандарты. Отсутствуют: ГОСТ Р 70628.2-2023 (ПЭ трубы), СП 252.1325800.2016.',
    recommendation: 'Дополнить перечень нормативных ссылок.',
  },
  {
    id: 7,
    docId: 1,
    docName: 'Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1_подпись (2).pdf',
    type: 'compliant',
    severity: null,
    title: 'Соответствие: Диаметры трубопроводов водоснабжения',
    sheet: 'Лист 3.1-02',
    norm: 'СП 30.13330.2020, п. 5.5.1',
    description:
      'Диаметры труб водоснабжения соответствуют расчётным значениям.',
    recommendation: null,
  },
  {
    id: 8,
    docId: 1,
    docName: 'Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1_подпись (2).pdf',
    type: 'compliant',
    severity: null,
    title: 'Соответствие: Тепловая изоляция трубопроводов',
    sheet: 'Лист 3.1-04',
    norm: 'СП 61.13330.2012',
    description:
      'Толщина изоляции ROCKWOOL 100 мм соответствует тепловым требованиям.',
    recommendation: null,
  },
  {
    id: 9,
    docId: 1,
    docName: 'Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1_подпись (2).pdf',
    type: 'compliant',
    severity: null,
    title: 'Соответствие: Схема канализации',
    sheet: 'Лист 3.1-03',
    norm: 'СП 30.13330.2020, п. 8.2.8',
    description:
      'Схема канализации с сифонами и вентиляцией соответствует требованиям.',
    recommendation: null,
  },
  {
    id: 10,
    docId: 1,
    docName: 'Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1_подпись (2).pdf',
    type: 'unchecked',
    severity: null,
    title: 'Не проверено: Пожарный водопровод',
    sheet: 'Лист 3.1-06',
    norm: null,
    description:
      'Система пожаротушения требует отдельной проверки на соответствие СП 10.13130.2020.',
    recommendation: null,
  },
];

let reportsData = [];
let currentFilter = 'all';
let currentSectionFilter = '';
let currentSeverityFilter = '';
let nextNormId = 2;
let nextDocId = 2;
let nextCheckId = 11;
let nextReportId = 1;

// ===== NAVIGATION =====
function navigateTo(section) {
  document.querySelectorAll('.nav-item').forEach((item) => {
    item.classList.remove('active');
    if (item.dataset.section === section) {
      item.classList.add('active');
    }
  });

  document
    .querySelectorAll('.section')
    .forEach((sec) => sec.classList.remove('active'));
  const sectionEl = document.getElementById(section + 'Section');
  if (sectionEl) sectionEl.classList.add('active');

  const titles = {
    dashboard: 'Dashboard',
    norms: 'Нормы',
    docs: 'Документация',
    checks: 'Проверки',
    reports: 'Отчёты',
    settings: 'Настройки',
  };
  document.getElementById('breadcrumbCurrent').textContent =
    titles[section] || section;
}

// ===== THEME =====
function toggleTheme() {
  const html = document.documentElement;
  const currentTheme = html.getAttribute('data-theme');
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', newTheme);

  const themeSwitch = document.getElementById('themeSwitch');
  if (newTheme === 'dark') {
    themeSwitch.classList.add('active');
  } else {
    themeSwitch.classList.remove('active');
  }
}

document.getElementById('themeToggle').addEventListener('click', toggleTheme);

// ===== TOAST =====
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = 'toast ' + type;

  const icons = { success: '✓', error: '✕', info: 'ℹ' };

  toast.innerHTML =
    '<div class="toast-icon">' +
    icons[type] +
    '</div>' +
    '<div class="toast-message">' +
    message +
    '</div>';

  container.appendChild(toast);

  setTimeout(function () {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(400px)';
    toast.style.transition = 'all 0.3s';
    setTimeout(function () {
      toast.remove();
    }, 300);
  }, 3000);
}

// ===== BADGES =====
function updateBadges() {
  document.getElementById('normsBadge').textContent = normsData.length;
  document.getElementById('docsBadge').textContent = docsData.length;
  document.getElementById('checksBadge').textContent = checksData.length;
  document.getElementById('reportsBadge').textContent = reportsData.length;
}

// ===== RENDER: REPORTS =====
function renderReports() {
  var list = document.getElementById('reportsList');
  if (reportsData.length === 0) {
    list.innerHTML =
      '<div style="text-align:center;padding:48px;color:var(--text-secondary);">Отчёты ещё не созданы. Нажмите «Создать отчёт» для генерации.</div>';
    return;
  }
  var html = '';
  for (var i = 0; i < reportsData.length; i++) {
    var report = reportsData[i];
    html += '<div class="report-item">';
    html += '<div class="report-header"><div>';
    html += '<div class="report-title">' + escapeHtml(report.title) + '</div>';
    html += '<div class="report-meta">Создан: ' + report.date + '</div>';
    html += '</div>';
    html += '<div style="display:flex;gap:8px;">';
    html +=
      '<button class="btn btn-primary btn-sm" onclick="downloadReportPDF(' +
      report.id +
      ')">PDF</button>';
    html +=
      '<button class="btn btn-secondary btn-sm" onclick="downloadReportWord(' +
      report.id +
      ')">Word</button>';
    html +=
      '<button class="btn btn-secondary btn-sm" onclick="downloadReportMarkdown(' +
      report.id +
      ')">MD</button>';
    html +=
      '<button class="btn btn-danger btn-sm" onclick="deleteReport(' +
      report.id +
      ')">Удалить</button>';
    html += '</div></div>';
    html += '<div class="report-stats">';
    html +=
      '<div class="report-stat"><div class="report-stat-label">Всего проверок</div><div class="report-stat-value">' +
      report.totalChecks +
      '</div></div>';
    html +=
      '<div class="report-stat"><div class="report-stat-label">Нарушения</div><div class="report-stat-value" style="color:var(--danger);">' +
      report.violations +
      '</div></div>';
    html +=
      '<div class="report-stat"><div class="report-stat-label">Соответствия</div><div class="report-stat-value" style="color:var(--success);">' +
      report.compliant +
      '</div></div>';
    html +=
      '<div class="report-stat"><div class="report-stat-label">Не проверено</div><div class="report-stat-value" style="color:var(--text-secondary);">' +
      report.unchecked +
      '</div></div>';
    html += '</div>';
    html += '</div>';
  }
  list.innerHTML = html;
}

function deleteReport(id) {
  reportsData = reportsData.filter(function (r) {
    return r.id !== id;
  });
  renderReports();
  updateBadges();
  showToast('Отчёт удалён', 'success');
}

// ===== GENERATE REPORT =====
// Knowledge Base Chat Functions
let chatHistory = [];

function fillExampleQuestion(element) {
  const question = element.textContent.trim();
  document.getElementById('chatInput').value = question;
  sendChatMessage();
}

function sendChatMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();

  if (!message) return;

  const searchInDocs = document.getElementById('searchInDocs').checked;

  // Clear input
  input.value = '';

  // Add user message to chat
  addMessageToChat('user', message);

  // Show typing indicator
  showTypingIndicator();

  // Send to API
  fetch('http://localhost:8000/api/knowledge-base/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question: message,
      search_in_docs: searchInDocs,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      hideTypingIndicator();

      if (data.error) {
        addMessageToChat('assistant', 'Ошибка: ' + data.error);
      } else {
        addMessageToChat('assistant', data.answer, data.sources);
      }
    })
    .catch((error) => {
      hideTypingIndicator();
      addMessageToChat(
        'assistant',
        'Ошибка подключения к серверу. Убедитесь, что сервер запущен на http://localhost:8000',
      );
      console.error('Chat error:', error);
    });
}

function addMessageToChat(role, content, sources = null) {
  const messagesContainer = document.getElementById('chatMessages');

  // Remove welcome message if present
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
  bubble.textContent = content;
  contentDiv.appendChild(bubble);

  // Add sources if available
  if (sources && sources.length > 0) {
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
      icon.innerHTML =
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>';

      const textDiv = document.createElement('div');
      textDiv.className = 'source-text';
      textDiv.textContent = source.text;

      const meta = document.createElement('div');
      meta.className = 'source-meta';
      meta.textContent = `${source.document} • Стр. ${source.page}`;

      textDiv.appendChild(meta);
      sourceItem.appendChild(icon);
      sourceItem.appendChild(textDiv);
      sourcesDiv.appendChild(sourceItem);
    });

    contentDiv.appendChild(sourcesDiv);
  }

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

  // Save to history
  chatHistory.push({ role, content, sources, timestamp: new Date() });
}

function showTypingIndicator() {
  const messagesContainer = document.getElementById('chatMessages');
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
  bubble.innerHTML =
    '<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>';

  contentDiv.appendChild(bubble);
  typingDiv.appendChild(avatar);
  typingDiv.appendChild(contentDiv);

  messagesContainer.appendChild(typingDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  // Disable send button
  document.getElementById('chatSendBtn').disabled = true;
}

function hideTypingIndicator() {
  const typing = document.getElementById('typingIndicator');
  if (typing) {
    typing.remove();
  }
  // Enable send button
  document.getElementById('chatSendBtn').disabled = false;
}

// Handle Enter key in chat input
document.addEventListener('DOMContentLoaded', function () {
  const chatInput = document.getElementById('chatInput');
  if (chatInput) {
    chatInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
      }
    });
  }

  // Update knowledge base counters
  updateKnowledgeBaseCounters();
});

function updateKnowledgeBaseCounters() {
  const normsCount = normsData ? normsData.length : 0;
  const docsCount = docsData ? docsData.length : 0;

  const normsBadge = document.getElementById('normsCount');
  const docsBadge = document.getElementById('docsCount');

  if (normsBadge) {
    normsBadge.textContent = `${normsCount} ${getWordForm(normsCount, 'норма', 'нормы', 'норм')} загружено`;
  }
  if (docsBadge) {
    docsBadge.textContent = `${docsCount} ${getWordForm(docsCount, 'документ', 'документа', 'документов')} загружено`;
  }
}

function getWordForm(number, one, two, five) {
  let n = Math.abs(number);
  n %= 100;
  if (n >= 5 && n <= 20) return five;
  n %= 10;
  if (n === 1) return one;
  if (n >= 2 && n <= 4) return two;
  return five;
}

// Knowledge Base Three-Panel Functions
let kbChatHistory = [];
let kbIsProcessing = false;

function toggleKBLeftSidebar() {
  const sidebar = document.getElementById('kbLeftSidebar');
  sidebar.classList.toggle('collapsed');
}

function toggleKBRightPanel() {
  const panel = document.getElementById('kbRightPanel');
  panel.classList.toggle('collapsed');
}

function newKBChat() {
  // Очистить историю чата
  kbChatHistory = [];
  const messagesContainer = document.getElementById('kbChatMessages');
  messagesContainer.innerHTML = `
                <div class="kb-welcome-screen" id="kbWelcomeScreen">
                    <div class="kb-welcome-icon">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                        </svg>
                    </div>
                    <h2>База знаний</h2>
                    <p>Задайте вопрос по нормативным документам или проектной документации. Система найдёт релевантную информацию и предоставит ответ с ссылками на источники.</p>
                    <div class="kb-example-queries">
                        <div class="kb-example-query" onclick="sendKBExample('Какие требования к диаметру труб для внутреннего водопровода согласно СП 30.13330.2020?')">
                            Какие требования к диаметру труб для внутреннего водопровода согласно СП 30.13330.2020?
                        </div>
                        <div class="kb-example-query" onclick="sendKBExample('Что говорит СП 30.13330.2020 о скорости воды в трубах и как её рассчитать?')">
                            Что говорит СП 30.13330.2020 о скорости воды в трубах и как её рассчитать?
                        </div>
                        <div class="kb-example-query" onclick="sendKBExample('Как рассчитать потери напора в трубопроводе по формуле Дарси-Вейсбаха?')">
                            Как рассчитать потери напора в трубопроводе по формуле Дарси-Вейсбаха?
                        </div>
                    </div>
                </div>
            `;
}

function sendKBExample(question) {
  const input = document.getElementById('kbChatInput');
  input.value = question;
  sendKBMessage();
}

function handleKBInputKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendKBMessage();
  }
}

function autoResizeKBInput(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
}

async function sendKBMessage() {
  const input = document.getElementById('kbChatInput');
  const message = input.value.trim();

  if (!message || kbIsProcessing) return;

  const searchInNorms = document.getElementById('kbSearchInNorms').checked;
  const searchInDocs = document.getElementById('kbSearchInDocs').checked;

  // Скрыть приветственный экран
  const welcomeScreen = document.getElementById('kbWelcomeScreen');
  if (welcomeScreen) {
    welcomeScreen.remove();
  }

  // Добавить сообщение пользователя
  addKBMessageToChat('user', message);
  input.value = '';
  input.style.height = 'auto';

  // Показать индикатор печати
  showKBTypingIndicator();
  kbIsProcessing = true;

  try {
    // Отправить запрос на backend
    const response = await fetch(
      `http://127.0.0.1:8000/api/knowledge-base/query`,
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

    // Скрыть индикатор печати
    hideKBTypingIndicator();

    // Добавить ответ AI
    addKBMessageToChat('ai', data.answer, data.sources);
  } catch (error) {
    console.error('Ошибка отправки запроса:', error);
    hideKBTypingIndicator();
    addKBMessageToChat(
      'ai',
      'Извините, произошла ошибка при обработке запроса. Пожалуйста, проверьте подключение к серверу и попробуйте снова.',
    );
  } finally {
    kbIsProcessing = false;
  }
}

function addKBMessageToChat(role, content, sources = null) {
  const messagesContainer = document.getElementById('kbChatMessages');

  const messageDiv = document.createElement('div');
  messageDiv.className = `kb-message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'kb-message-avatar';
  avatar.textContent = role === 'user' ? 'Вы' : 'AI';

  const contentDiv = document.createElement('div');
  contentDiv.className = 'kb-message-content';
  contentDiv.textContent = content;

  // Добавить источники, если есть
  if (sources && sources.length > 0) {
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
      sourceText.textContent = source.text;

      const sourceMeta = document.createElement('div');
      sourceMeta.className = 'kb-source-meta';
      sourceMeta.textContent = `${source.document} • Стр. ${source.page}`;

      sourceItem.appendChild(sourceText);
      sourceItem.appendChild(sourceMeta);
      sourcesDiv.appendChild(sourceItem);
    });

    contentDiv.appendChild(sourcesDiv);
  }

  messageDiv.appendChild(avatar);
  messageDiv.appendChild(contentDiv);
  messagesContainer.appendChild(messageDiv);

  // Прокрутить вниз
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  // Сохранить в историю
  kbChatHistory.push({ role, content, sources });
}

function showKBTypingIndicator() {
  const messagesContainer = document.getElementById('kbChatMessages');

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

  // Прокрутить вниз
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function hideKBTypingIndicator() {
  const indicator = document.getElementById('kbTypingIndicator');
  if (indicator) {
    indicator.remove();
  }
}

function showProgressModal() {
  document.getElementById('progressModalOverlay').classList.add('active');
}

function hideProgressModal() {
  document.getElementById('progressModalOverlay').classList.remove('active');
}

function updateProgress(percent, timeLeft) {
  // Обновляем процент
  document.getElementById('progressPercent').textContent = percent + '%';
  document.getElementById('progressBarText').textContent = percent + '%';
  document.getElementById('progressBarFill').style.width = percent + '%';

  // Обновляем оставшееся время
  if (timeLeft > 0) {
    document.getElementById('progressTime').textContent =
      'Осталось: ~' + timeLeft + ' сек';
  } else {
    document.getElementById('progressTime').textContent = 'Завершено!';
  }
}

function updateStage(stageNumber) {
  const stages = document.querySelectorAll('.progress-stage');
  stages.forEach((stage, index) => {
    const stageNum = parseInt(stage.dataset.stage);
    if (stageNum < stageNumber) {
      stage.classList.remove('active');
      stage.classList.add('completed');
    } else if (stageNum === stageNumber) {
      stage.classList.add('active');
      stage.classList.remove('completed');
    } else {
      stage.classList.remove('active', 'completed');
    }
  });
}

function simulateReportGeneration() {
  const totalDuration = 10000; // 10 секунд
  const interval = 100; // Обновление каждые 100мс
  const steps = totalDuration / interval;
  let currentStep = 0;

  const intervalId = setInterval(() => {
    currentStep++;
    const percent = Math.floor((currentStep / steps) * 100);
    const timeLeft = Math.ceil(((steps - currentStep) * interval) / 1000);

    updateProgress(percent, timeLeft);

    // Обновляем этапы
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
      clearInterval(intervalId);
      completeReportGeneration();
    }
  }, interval);
}

function completeReportGeneration() {
  // Создаём отчёт
  var violations = checksData.filter(function (c) {
    return c.type === 'violation';
  }).length;
  var compliant = checksData.filter(function (c) {
    return c.type === 'compliant';
  }).length;
  var unchecked = checksData.filter(function (c) {
    return c.type === 'unchecked';
  }).length;
  var critical = checksData.filter(function (c) {
    return c.severity === 'critical';
  }).length;
  var major = checksData.filter(function (c) {
    return c.severity === 'major';
  }).length;
  var minor = checksData.filter(function (c) {
    return c.severity === 'minor';
  }).length;

  var report = {
    id: nextReportId++,
    title:
      'Отчёт по проверкам от ' +
      new Date().toLocaleDateString('ru-RU') +
      ' ' +
      new Date().toLocaleTimeString('ru-RU'),
    date: new Date().toLocaleDateString('ru-RU'),
    totalChecks: checksData.length,
    violations: violations,
    compliant: compliant,
    unchecked: unchecked,
    critical: critical,
    major: major,
    minor: minor,
    checks: checksData.slice(),
  };

  reportsData.push(report);
  renderReports();
  updateBadges();

  // Скрываем модальное окно и показываем уведомление
  setTimeout(() => {
    hideProgressModal();
    showToast('Отчёт успешно создан', 'success');
  }, 500);
}

// ===== UTILITY =====
function escapeHtml(text) {
  if (!text) return '';
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

// ===== FILTER HANDLERS =====
document.querySelectorAll('.filter-tab').forEach(function (tab) {
  tab.addEventListener('click', function () {
    document.querySelectorAll('.filter-tab').forEach(function (t) {
      t.classList.remove('active');
    });
    this.classList.add('active');
    currentFilter = this.dataset.filter;
    renderChecks();
  });
});

// ===== ИНИЦИАЛИЗАЦИЯ ПОСЛЕ ЗАГРУЗКИ DOM =====
document.addEventListener('DOMContentLoaded', function () {
  // Обработчики навигации
  document.querySelectorAll('.nav-item').forEach(function (item) {
    item.addEventListener('click', function () {
      navigateTo(this.dataset.section);
    });
  });

  // Обработчики dropzone
  var normsDropzone = document.getElementById('normsDropzone');
  if (normsDropzone) {
    normsDropzone.addEventListener('dragover', handleDragOver);
    normsDropzone.addEventListener('dragleave', handleDragLeave);
    normsDropzone.addEventListener('drop', function (e) {
      handleDrop(e, 'norms');
    });
  }

  var docsDropzone = document.getElementById('docsDropzone');
  if (docsDropzone) {
    docsDropzone.addEventListener('dragover', handleDragOver);
    docsDropzone.addEventListener('dragleave', handleDragLeave);
    docsDropzone.addEventListener('drop', function (e) {
      handleDrop(e, 'docs');
    });
  }

  // Инициализация данных
  renderNorms();
  renderDocs();
  renderChecks();
  renderReports();
  renderDashboardTable();
  updateBadges();
  loadStoragePaths();
});

// ===== KEYBOARD SHORTCUTS =====
document.addEventListener('keydown', function (e) {
  if (e.ctrlKey) {
    switch (e.key) {
      case '1':
        e.preventDefault();
        navigateTo('dashboard');
        break;
      case '2':
        e.preventDefault();
        navigateTo('norms');
        break;
      case '3':
        e.preventDefault();
        navigateTo('docs');
        break;
      case '4':
        e.preventDefault();
        navigateTo('checks');
        break;
      case '5':
        e.preventDefault();
        navigateTo('reports');
        break;
      case '6':
        e.preventDefault();
        navigateTo('settings');
        break;
      case 'k':
      case 'K':
        e.preventDefault();
        document.querySelector('.search-input').focus();
        break;
      case 'd':
      case 'D':
        e.preventDefault();
        toggleTheme();
        break;
      case '?':
        e.preventDefault();
        document.getElementById('shortcutsOverlay').classList.add('active');
        break;
    }
  }
  if (e.key === 'Escape') {
    document.getElementById('shortcutsOverlay').classList.remove('active');
  }
});

function closeShortcuts() {
  document.getElementById('shortcutsOverlay').classList.remove('active');
}

// ===== INITIALIZE =====
// Инициализация перенесена в DOMContentLoaded (см. выше)
