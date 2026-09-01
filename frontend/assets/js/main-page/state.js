// ============================================================
// VKS EXPERT AI — runtime state
// ============================================================

var currentSection = 'dashboard';
var currentFilter = 'all';
var currentSeverityFilter = '';
var currentSectionFilter = 'all';

var docsData = [];
var normsData = [];
var checksData = [];

// Results are kept only for the current application data schema. Old demo
// values from previous builds must never reappear in the real dashboard.
var CHECKS_STORAGE_VERSION = 'v2-real-checks';
try {
  var savedChecksVersion = localStorage.getItem('projectExpertAI.checks.version');
  if (savedChecksVersion === CHECKS_STORAGE_VERSION) {
    var savedChecks = JSON.parse(localStorage.getItem('projectExpertAI.checks') || '[]');
    if (Array.isArray(savedChecks)) checksData = savedChecks;
  } else {
    localStorage.removeItem('projectExpertAI.checks');
    localStorage.setItem('projectExpertAI.checks.version', CHECKS_STORAGE_VERSION);
  }
} catch (error) {
  console.warn('[VKS Expert AI] Не удалось загрузить сохраненные результаты проверок:', error);
}

var nextDocId = 1;
var nextNormId = 1;
var currentReport = null;
var reportsData = [];
try {
  var savedReports = JSON.parse(localStorage.getItem('projectExpertAI.reports') || '[]');
  if (Array.isArray(savedReports)) reportsData = savedReports;
} catch (error) {
  console.warn('[VKS Expert AI] Не удалось загрузить сохраненные отчеты:', error);
}

var settingsData = {
  autoCheck: true,
  autoIndex: true,
  aiModel: 'Qwen3.5-9B',
  temperature: 0.2,
  checkSections: ['ВК', 'ОВ', 'ЭОМ'],
  includeRecommendations: true,
  compactMode: false,
  showTechnicalDetails: false,
  reportFormat: 'pdf',
};

var indexingState = { active: false, total: 0, completed: 0, currentNormId: null };
var checkingState = { active: false, total: 0, completed: 0, documentIds: [] };

var appStats = {
  totalChecks: checksData.length,
  totalViolations: checksData.filter(function (x) { return x.type === 'violation'; }).length,
  totalCompliant: checksData.filter(function (x) { return x.type === 'compliant'; }).length,
  totalUnchecked: checksData.filter(function (x) { return x.type === 'unchecked'; }).length,
  totalCritical: checksData.filter(function (x) { return x.type === 'violation' && x.severity === 'critical'; }).length,
};

// Public runtime state. Renderers are ES modules, therefore they must use the
// window object instead of relying on another script's lexical scope.
window.docsData = docsData;
window.normsData = normsData;
window.checksData = checksData;
window.appStats = appStats;
window.currentReport = currentReport;
window.reportsData = reportsData;
window.settingsData = settingsData;
window.indexingState = indexingState;
window.checkingState = checkingState;

function getDocumentById(id) { return window.docsData.find(function (doc) { return String(doc.id) === String(id); }); }
function getNormById(id) { return window.normsData.find(function (norm) { return String(norm.id) === String(id); }); }
function getCheckById(id) { return window.checksData.find(function (check) { return String(check.id) === String(id); }); }
function getNextCheckId() { if (!window.checksData.length) return 1; return Math.max.apply(null, window.checksData.map(function (x) { return Number(x.id) || 0; })) + 1; }

console.log('[VKS Expert AI] state.js загружен — только реальные результаты проверок');
