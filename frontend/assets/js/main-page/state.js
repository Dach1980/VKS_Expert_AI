// ============================================================
// VKS EXPERT AI — runtime state
// ============================================================

var currentSection = 'dashboard';
var currentFilter = 'all';
var currentSeverityFilter = '';
var currentSectionFilter = 'all';

// Data comes from backend. Demo project/check values are intentionally absent.
var docsData = [];
var normsData = [];
var checksData = [];

try {
  var savedChecks = JSON.parse(localStorage.getItem('projectExpertAI.checks') || '[]');
  if (Array.isArray(savedChecks)) checksData = savedChecks;
} catch (error) {
  console.warn('[VKS Expert AI] Не удалось загрузить сохраненные результаты проверок:', error);
}

var nextDocId = 1;
var nextNormId = 1;
var currentReport = null;
var reportsData = [];
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

// Real statistics are calculated from checksData by dashboard.js.
var appStats = {
  totalChecks: checksData.length,
  totalViolations: checksData.filter(function (x) { return x.type === 'violation'; }).length,
  totalCompliant: checksData.filter(function (x) { return x.type === 'compliant'; }).length,
  totalUnchecked: checksData.filter(function (x) { return x.type === 'unchecked'; }).length,
  totalCritical: checksData.filter(function (x) { return x.type === 'violation' && x.severity === 'critical'; }).length,
};

function getDocumentById(id) { return docsData.find(function (doc) { return String(doc.id) === String(id); }); }
function getNormById(id) { return normsData.find(function (norm) { return String(norm.id) === String(id); }); }
function getCheckById(id) { return checksData.find(function (check) { return String(check.id) === String(id); }); }
function getNextCheckId() {
  if (!checksData.length) return 1;
  return Math.max.apply(null, checksData.map(function (x) { return Number(x.id) || 0; })) + 1;
}

console.log('[VKS Expert AI] state.js загружен — demo-результаты отключены');
