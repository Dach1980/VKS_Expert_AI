// ============================================================
// state.js
// ЕДИНОЕ СОСТОЯНИЕ ПРИЛОЖЕНИЯ
// ============================================================
//
// Этот файл должен загружаться ПЕРЕД:
// dashboard.js
// norms.js
// documents.js
// checks.js
// reports.js
// settings.js
//
// Все переменные объявлены через window, чтобы они были
// доступны из остальных JavaScript-файлов приложения.
// ============================================================

console.log('[MAX? / VK NormControl] state.js загружен');

// ============================================================
// DOCUMENTS
// ============================================================

var docsData = [
  {
    id: 1,
    name: '35020 040002.111.20.-3.1_ИОС3.1_Изм.1.pdf',
    size: '2.4 МБ',
    date: '2026-05-21',
    status: 'new',
    sheets: 8,
    section: 'ВК',
    checked: false,
  },
];

// ============================================================
// NORMS
// ============================================================

var normsData = [
  {
    id: 1,
    title: 'СП 30.13330.2020',
    subtitle: 'Внутренний водопровод и канализация зданий',
    date: '2026-05-20',
    points: 250,
    status: 'indexed',
    progress: 100,
    sections: ['ВК'],
    fileName: 'СП 30.13330.2020.pdf',
  },
  {
    id: 2,
    title: 'СП 32.13330.2018',
    subtitle: 'Канализация. Наружные сети и сооружения',
    date: '2026-05-20',
    points: 320,
    status: 'indexed',
    progress: 100,
    sections: ['ВК'],
    fileName: 'СП 32.13330.2018.pdf',
  },
  {
    id: 3,
    title: 'ГОСТ 8732-78',
    subtitle: 'Трубы стальные бесшовные горячедеформированные',
    date: '2026-05-19',
    points: 180,
    status: 'indexed',
    progress: 100,
    sections: ['ВК'],
    fileName: 'ГОСТ 8732-78.pdf',
  },
  {
    id: 4,
    title: 'ГОСТ 10704-91',
    subtitle: 'Трубы стальные электросварные прямошовные',
    date: '2026-05-19',
    points: 145,
    status: 'indexed',
    progress: 100,
    sections: ['ВК'],
    fileName: 'ГОСТ 10704-91.pdf',
  },
];

// ============================================================
// CHECKS
// ============================================================

var checksData = [];

// ============================================================
// REPORTS
// ============================================================

var reportsData = [];

// ============================================================
// FILTERS
// ============================================================

// Общий фильтр типа проверки
var currentFilter = 'all';

// Фильтр по критичности
var currentSeverityFilter = '';

// Фильтр по разделу
var currentSectionFilter = 'all';

// ============================================================
// ID COUNTERS
// ============================================================

var nextDocId = getNextId(docsData);
var nextNormId = getNextId(normsData);
var nextCheckId = getNextId(checksData);
var nextReportId = getNextId(reportsData);

// ============================================================
// APPLICATION STATE
// ============================================================

var appState = {
  initialized: false,
  currentSection: 'dashboard',
  isChecking: false,
  isGeneratingReport: false,
};

// ============================================================
// HELPERS
// ============================================================

function getNextId(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return 1;
  }

  var maxId = 0;

  for (var i = 0; i < items.length; i++) {
    var id = Number(items[i].id);

    if (!isNaN(id) && id > maxId) {
      maxId = id;
    }
  }

  return maxId + 1;
}

// ============================================================
// STATE INITIALIZATION
// ============================================================

function initializeState() {
  console.log('[State] Инициализация состояния приложения');

  nextDocId = getNextId(docsData);
  nextNormId = getNextId(normsData);
  nextCheckId = getNextId(checksData);
  nextReportId = getNextId(reportsData);

  appState.initialized = true;

  console.log('[State] Документов:', docsData.length);
  console.log('[State] Нормативных документов:', normsData.length);
  console.log('[State] Проверок:', checksData.length);
  console.log('[State] Отчётов:', reportsData.length);

  console.log('[State] Следующий ID документа:', nextDocId);
  console.log('[State] Следующий ID нормы:', nextNormId);
  console.log('[State] Следующий ID проверки:', nextCheckId);
  console.log('[State] Следующий ID отчёта:', nextReportId);
}

// ============================================================
// STATE RESET
// ============================================================

function resetApplicationState() {
  docsData = [];
  normsData = [];
  checksData = [];
  reportsData = [];

  currentFilter = 'all';
  currentSeverityFilter = '';
  currentSectionFilter = 'all';

  nextDocId = 1;
  nextNormId = 1;
  nextCheckId = 1;
  nextReportId = 1;

  appState.currentSection = 'dashboard';
  appState.isChecking = false;
  appState.isGeneratingReport = false;

  console.log('[State] Состояние приложения сброшено');

  if (typeof renderDocs === 'function') {
    renderDocs();
  }

  if (typeof renderNorms === 'function') {
    renderNorms();
  }

  if (typeof renderChecks === 'function') {
    renderChecks();
  }

  if (typeof renderDashboardTable === 'function') {
    renderDashboardTable();
  }

  if (typeof updateDashboardMetrics === 'function') {
    updateDashboardMetrics();
  }

  if (typeof updateBadges === 'function') {
    updateBadges();
  }
}

// ============================================================
// GLOBAL WINDOW REFERENCES
// ============================================================
//
// Явно экспортируем состояние в window.
// Это особенно полезно, если в будущем часть приложения
// будет переведена на модули.
//
// ============================================================

window.docsData = docsData;
window.normsData = normsData;
window.checksData = checksData;
window.reportsData = reportsData;

window.currentFilter = currentFilter;
window.currentSeverityFilter = currentSeverityFilter;
window.currentSectionFilter = currentSectionFilter;

window.appState = appState;

// ============================================================
// START
// ============================================================

initializeState();

console.log('[State] state.js готов');
